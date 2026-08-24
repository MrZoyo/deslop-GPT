#!/usr/bin/env python3
import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path


EXPECTED_VERSION = "0.7.0"
CODEX_SKILL_PATH = ".agents/skills"


def option_value(arguments: list[str], option: str) -> str | None:
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(f"{option}="):
            return argument.split("=", 1)[1]
    return None


def configure_skill_name(skill_argument: str, evals_argument: str) -> None:
    from agent_skill_eval.skills import SkillInstaller

    skill_path = Path(skill_argument).resolve()
    suite = json.loads(Path(evals_argument).read_text())
    expected_name = suite.get("skill_name")
    if not isinstance(expected_name, str) or not expected_name:
        raise RuntimeError("eval suite must declare a non-empty skill_name")

    installer = SkillInstaller(skill_path)
    installer.skill_name = expected_name
    problems = installer.frontmatter_problems()
    if problems:
        raise RuntimeError("invalid Skill metadata: " + "; ".join(problems))

    original_init = SkillInstaller.__init__

    def normalized_init(self, path: Path) -> None:
        original_init(self, path)
        if Path(path).resolve() == skill_path:
            self.skill_name = expected_name

    SkillInstaller.__init__ = normalized_init


def configure_side_effect_contract() -> None:
    from agent_skill_eval.graders import summarize_assertion_results
    from agent_skill_eval.models import AssertionResult, GradingResult
    from agent_skill_eval.runner import EvalRunner

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
            before = set(pre_state.status_porcelain)
            after = set(post_state.status_porcelain)
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
    print("Side-effect contract pre/post self-test passed", file=sys.stderr)


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
        configure_skill_name(skill_argument, evals_argument)
        configure_side_effect_contract()
        smoke_test(skill_argument, check_ambient=command == "run")
        if command == "self-test":
            side_effect_contract_self_test()
            print(f"agent-skill-eval {installed_version} wrapper self-test passed")
            return

    from agent_skill_eval.cli import app

    app()


if __name__ == "__main__":
    main()
