#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor as NativeThreadPoolExecutor
from concurrent.futures import as_completed as native_as_completed
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable


EXPECTED_VERSION = "0.7.0"
CODEX_SKILL_PATH = ".agents/skills"
AB_ORDER = "deterministic-counterbalanced"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
IGNORED_STATUS_MARKERS = (
    "__pycache__/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".pyc",
)
_ACTIVE_EXECUTOR = None


def counterbalanced_indices(
    identities: list[tuple[str, str, bool, int]],
) -> list[int]:
    case_positions: dict[str, int] = {}
    groups: dict[tuple[str, str, int], list[tuple[int, bool]]] = {}
    group_order: list[tuple[str, str, int]] = []

    for index, (eval_id, agent, with_skill, run_index) in enumerate(identities):
        if eval_id not in case_positions:
            case_positions[eval_id] = len(case_positions) + 1
        key = (eval_id, agent, run_index)
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append((index, with_skill))

    ordered: list[int] = []
    for eval_id, agent, run_index in group_order:
        entries = groups[(eval_id, agent, run_index)]
        skill_first = (case_positions[eval_id] + run_index) % 2 == 0
        entries.sort(key=lambda entry: entry[1] != skill_first)
        ordered.extend(index for index, _ in entries)
    return ordered


class CounterbalancedExecutor:
    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs
        self.calls: list[tuple[Future, Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []
        self.executor: NativeThreadPoolExecutor | None = None

    def __enter__(self):
        global _ACTIVE_EXECUTOR
        if _ACTIVE_EXECUTOR is not None:
            raise RuntimeError("counterbalanced executor does not support nesting")
        _ACTIVE_EXECUTOR = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global _ACTIVE_EXECUTOR
        try:
            self.start()
            if self.executor is not None:
                self.executor.shutdown(wait=True)
        finally:
            _ACTIVE_EXECUTOR = None

    def submit(self, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        future = Future()
        self.calls.append((future, function, args, kwargs))
        return future

    def start(self) -> None:
        if self.executor is not None:
            return
        self.executor = NativeThreadPoolExecutor(*self.args, **self.kwargs)
        identities = []
        for _, _, args, _ in self.calls:
            eval_case, agent_type, with_skill = args[:3]
            run_index = args[5] if len(args) > 5 else 1
            identities.append(
                (str(eval_case.id), str(agent_type.value), bool(with_skill), int(run_index))
            )
        for index in counterbalanced_indices(identities):
            proxy, function, args, kwargs = self.calls[index]
            actual = self.executor.submit(function, *args, **kwargs)
            actual.add_done_callback(
                lambda completed, destination=proxy: transfer_future(completed, destination)
            )


def transfer_future(source: Future, destination: Future) -> None:
    if source.cancelled():
        destination.cancel()
        return
    error = source.exception()
    if error is not None:
        destination.set_exception(error)
    else:
        destination.set_result(source.result())


def counterbalanced_as_completed(futures, timeout=None):
    if _ACTIVE_EXECUTOR is not None:
        _ACTIVE_EXECUTOR.start()
    return native_as_completed(futures, timeout=timeout)


def option_value(arguments: list[str], option: str) -> str | None:
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(f"{option}="):
            return argument.split("=", 1)[1]
    return None


def validate_skill_identity(skill_argument: str, evals_argument: str) -> None:
    from agent_skill_eval.skills import SkillInstaller

    skill_path = Path(skill_argument).resolve()
    suite = json.loads(Path(evals_argument).read_text())
    expected_name = suite.get("skill_name")
    if not isinstance(expected_name, str) or not expected_name:
        raise RuntimeError("eval suite must declare a non-empty skill_name")

    installer = SkillInstaller(skill_path)
    problems = installer.frontmatter_problems()
    if problems:
        raise RuntimeError("invalid Skill metadata: " + "; ".join(problems))
    if installer.skill_name != expected_name:
        raise RuntimeError(
            f"eval suite skill_name {expected_name!r} does not match Skill directory "
            f"{installer.skill_name!r}"
        )


def configure_side_effect_contract() -> None:
    from agent_skill_eval.graders import summarize_assertion_results
    from agent_skill_eval.models import AssertionResult, GradingResult
    from agent_skill_eval.runner import EvalRunner

    def meaningful_status(entries):
        return {
            entry
            for entry in entries
            if not any(marker in entry for marker in IGNORED_STATUS_MARKERS)
        }

    def apply_contract(self, grading, eval_case, pre_state, post_state):
        contract = eval_case.side_effect_contract
        if contract is None:
            return grading

        problems = []
        new_local = sorted(set(post_state.local_branches) - set(pre_state.local_branches))
        new_remote = sorted(set(post_state.remote_branches) - set(pre_state.remote_branches))
        new_commits = sorted(set(post_state.commit_shas) - set(pre_state.commit_shas))
        pre_reviews = {item.get("number") for item in pre_state.open_prs}
        new_reviews = sorted(
            str(item.get("number"))
            for item in post_state.open_prs
            if item.get("number") is not None and item.get("number") not in pre_reviews
        )

        if new_local and not contract.allow_new_local_branches:
            problems.append("new local branches: " + ", ".join(new_local))
        if new_remote and not contract.allow_new_remote_branches:
            problems.append("new remote branches: " + ", ".join(new_remote))
        if new_commits and not contract.allow_new_commits:
            problems.append(f"new commits: {len(new_commits)}")
        if new_reviews and not contract.allow_new_review_requests:
            problems.append("new review requests: " + ", ".join(new_reviews))
        if not contract.allow_worktree_changes:
            before = meaningful_status(pre_state.status_porcelain)
            after = meaningful_status(post_state.status_porcelain)
            added = sorted(after - before)
            removed = sorted(before - after)
            if added or removed:
                problems.append(f"worktree status changed: added={added}; removed={removed}")

        result = AssertionResult(
            text="The run respected its side-effect contract",
            passed=not problems,
            evidence="ok" if not problems else "; ".join(problems),
            method="side-effect-contract",
        )
        all_results = list(grading.assertion_results) + [result]
        return GradingResult(
            assertion_results=all_results,
            summary=summarize_assertion_results(all_results),
        )

    EvalRunner._apply_side_effect_contract = apply_contract


def configure_task_order() -> None:
    import agent_skill_eval.runner as runner
    from agent_skill_eval.runner import EvalRunner

    runner.ThreadPoolExecutor = CounterbalancedExecutor
    runner.as_completed = counterbalanced_as_completed
    save_eval_metadata = EvalRunner._save_eval_metadata

    def save_with_reproducibility_metadata(self, iteration_dir):
        save_eval_metadata(self, iteration_dir)
        metadata_path = iteration_dir / "evals_meta.json"
        metadata = json.loads(metadata_path.read_text())
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        metadata["benchmark_repository"] = {
            "commit": commit,
            "dirty": dirty,
        }
        metadata["execution"] = {
            "concurrency": self.concurrency,
            "agent_timeout_seconds": self.agent_timeout,
            "agent_max_retries": self.agent_max_retries,
            "runs_per_case": self.runs,
            "with_baseline": self.with_baseline,
        }
        metadata["task_order"] = {
            "strategy": AB_ORDER,
            "rule": "Skill first when case_position + run_index is even; baseline first otherwise.",
            "case_order": [str(eval_case.id) for eval_case in self.suite.evals],
        }
        metadata["codex_environment"] = {
            "sandbox": "workspace-write",
            "network": "not-explicitly-pinned-or-recorded",
            "approval_policy": "not-pinned-by-harness",
            "local_config": "inherited-except-model-and-reasoning",
        }
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    EvalRunner._save_eval_metadata = save_with_reproducibility_metadata


def ambient_skill_paths(skill_name: str) -> list[Path]:
    user_home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", user_home / ".codex"))
    candidates = {
        user_home / CODEX_SKILL_PATH / skill_name,
        codex_home / "skills" / skill_name,
        Path("/etc/codex/skills") / skill_name,
    }
    return sorted(path for path in candidates if path.exists())


def smoke_test(skill_argument: str, *, check_ambient: bool) -> None:
    from agent_skill_eval.models import AgentType
    from agent_skill_eval.skills import SkillInstaller

    skill_path = Path(skill_argument).resolve()
    installer = SkillInstaller(skill_path)
    existing_ambient_paths = ambient_skill_paths(installer.skill_name) if check_ambient else []
    if existing_ambient_paths:
        paths = ", ".join(str(path) for path in existing_ambient_paths)
        raise RuntimeError(
            f"ambient Skill path(s) would contaminate the without-Skill baseline: {paths}; "
            "run the benchmark from a clean user profile or container"
        )
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        installed_path = installer.install(workspace, AgentType.CODEX)
        expected_path = workspace / CODEX_SKILL_PATH / installer.skill_name
        if installed_path != expected_path or not (installed_path / "SKILL.md").is_file():
            raise RuntimeError("Codex skill discovery smoke test did not use .agents/skills")
        installed_hash = SkillInstaller(installed_path).content_hash()
        if installed_hash != installer.content_hash():
            raise RuntimeError("Codex skill discovery smoke test found a content hash mismatch")
    print(
        f"Codex skill discovery smoke test passed: "
        f"path={CODEX_SKILL_PATH}/{installer.skill_name} hash={installed_hash}",
        file=sys.stderr,
    )


def side_effect_contract_self_test() -> None:
    from agent_skill_eval.graders import summarize_assertion_results
    from agent_skill_eval.models import (
        AssertionResult,
        EvalCase,
        GitStateSnapshot,
        GradingResult,
    )
    from agent_skill_eval.runner import EvalRunner

    assertion = AssertionResult(text="seed", passed=True, evidence="ok")
    grading = GradingResult(
        assertion_results=[assertion],
        summary=summarize_assertion_results([assertion]),
    )
    case = EvalCase(
        id="self-test",
        prompt="self-test",
        expected_output="self-test",
        side_effect_contract={
            "allow_new_local_branches": False,
            "allow_new_remote_branches": False,
            "allow_new_commits": False,
            "allow_new_review_requests": False,
            "allow_worktree_changes": False,
        },
    )
    before = GitStateSnapshot(
        local_branches=["main"],
        current_branch="main",
        head_sha="abc",
        commit_shas=["abc"],
        status_porcelain=["?? app.py"],
    )
    unchanged = EvalRunner._apply_side_effect_contract(None, grading, case, before, before)
    if not unchanged.assertion_results[-1].passed:
        raise RuntimeError("side-effect contract rejected an unchanged pre/post state")

    changed = before.model_copy(update={"status_porcelain": ["?? app.py", "?? audit-report.md"]})
    mutated = EvalRunner._apply_side_effect_contract(None, grading, case, before, changed)
    if mutated.assertion_results[-1].passed:
        raise RuntimeError("side-effect contract accepted a changed worktree state")

    git_changed = before.model_copy(
        update={"local_branches": ["main", "agent-change"], "commit_shas": ["abc", "def"]}
    )
    mutated_git = EvalRunner._apply_side_effect_contract(None, grading, case, before, git_changed)
    if mutated_git.assertion_results[-1].passed:
        raise RuntimeError("side-effect contract accepted a new branch and commit")

    cache_only = before.model_copy(
        update={"status_porcelain": ["?? app.py", "?? __pycache__/app.cpython-313.pyc"]}
    )
    cache_result = EvalRunner._apply_side_effect_contract(None, grading, case, before, cache_only)
    if not cache_result.assertion_results[-1].passed:
        raise RuntimeError("side-effect contract treated ignored Python cache as a worktree mutation")
    print("Side-effect contract pre/post self-test passed", file=sys.stderr)


def task_order_self_test() -> None:
    identities = [
        ("c01a", "codex", True, 1),
        ("c01a", "codex", False, 1),
        ("c01a", "codex", True, 2),
        ("c01a", "codex", False, 2),
        ("c01b", "codex", True, 1),
        ("c01b", "codex", False, 1),
        ("c01b", "codex", True, 2),
        ("c01b", "codex", False, 2),
    ]
    actual = [identities[index] for index in counterbalanced_indices(identities)]
    expected = [
        ("c01a", "codex", True, 1),
        ("c01a", "codex", False, 1),
        ("c01a", "codex", False, 2),
        ("c01a", "codex", True, 2),
        ("c01b", "codex", False, 1),
        ("c01b", "codex", True, 1),
        ("c01b", "codex", True, 2),
        ("c01b", "codex", False, 2),
    ]
    if actual != expected:
        raise RuntimeError("deterministic A/B counterbalancing self-test failed")

    executed = []

    def record(eval_case, agent_type, with_skill, iteration_dir, iteration, run_index):
        identity = (str(eval_case.id), str(agent_type.value), bool(with_skill), int(run_index))
        executed.append(identity)
        return identity

    futures = []
    with CounterbalancedExecutor(max_workers=1) as executor:
        for eval_id, agent, with_skill, run_index in identities:
            futures.append(
                executor.submit(
                    record,
                    SimpleNamespace(id=eval_id),
                    SimpleNamespace(value=agent),
                    with_skill,
                    None,
                    1,
                    run_index,
                )
            )
        for future in counterbalanced_as_completed(futures):
            future.result()
    if executed != expected:
        raise RuntimeError("counterbalanced executor did not preserve the planned order")
    print("Deterministic A/B counterbalancing self-test passed", file=sys.stderr)


def main() -> None:
    installed_version = version("agent-skill-eval")
    if installed_version != EXPECTED_VERSION:
        raise RuntimeError(
            f"expected agent-skill-eval {EXPECTED_VERSION}, found {installed_version}"
        )

    from agent_skill_eval.models import AgentType
    from agent_skill_eval.skills import SKILL_PATHS

    SKILL_PATHS[AgentType.CODEX] = [CODEX_SKILL_PATH]
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command in {"run", "self-test"}:
        arguments = sys.argv[2:]
        skill_argument = option_value(arguments, "--skill") or option_value(arguments, "-s")
        evals_argument = option_value(arguments, "--evals") or option_value(arguments, "-e")
        if skill_argument is None or evals_argument is None:
            raise RuntimeError(f"{command} requires --skill and --evals")
        validate_skill_identity(skill_argument, evals_argument)
        configure_side_effect_contract()
        configure_task_order()
        smoke_test(skill_argument, check_ambient=command == "run")
        if command == "self-test":
            side_effect_contract_self_test()
            task_order_self_test()
            print(f"agent-skill-eval {installed_version} wrapper self-test passed")
            return

    from agent_skill_eval.cli import app

    app()


if __name__ == "__main__":
    main()
