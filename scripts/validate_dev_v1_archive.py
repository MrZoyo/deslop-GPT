#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "evals" / "archive" / "dev-v1"
SKILL_ROOT = ROOT / "skills" / "deslop"
EVALS_PATH = ARCHIVE_ROOT / "evals.json"
ADJUDICATION_PATH = ARCHIVE_ROOT / "adjudication.json"
CALIBRATION_ROOT = ARCHIVE_ROOT / "calibration"
CASE_ID = re.compile(r"c(0[1-9]|10)[ab]")
SIDE_EFFECT_CONTRACT_KEYS = {
    "allow_new_local_branches",
    "allow_new_remote_branches",
    "allow_new_commits",
    "allow_new_review_requests",
    "allow_worktree_changes",
}


def fail(message: str) -> None:
    raise ValueError(message)


def skill_content_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_skill() -> None:
    skill_text = (SKILL_ROOT / "SKILL.md").read_text()
    if not skill_text.startswith("---\n"):
        fail("SKILL.md is missing YAML frontmatter")
    frontmatter = skill_text.split("---", 2)[1]
    if "\nname: deslop\n" not in f"\n{frontmatter}\n":
        fail("SKILL.md must declare name: deslop")
    if "\ndescription:" not in f"\n{frontmatter}\n":
        fail("SKILL.md is missing description")
    if len(skill_text.splitlines()) > 200:
        fail("SKILL.md exceeds the 200-line public entrypoint budget")
    if "TODO" in skill_text or "$ARGUMENTS" in skill_text:
        fail("SKILL.md contains a placeholder or runtime-specific arguments variable")

    required_references = {
        "references/code-smells.md",
        "references/test-smells.md",
        "references/verification-and-trust.md",
        "references/scientific-code.md",
        "references/evidence-and-reachability.md",
    }
    for reference in required_references:
        if reference not in skill_text or not (SKILL_ROOT / reference).is_file():
            fail(f"SKILL.md does not route to {reference}")

    openai_yaml = (SKILL_ROOT / "agents" / "openai.yaml").read_text()
    if "allow_implicit_invocation: false" not in openai_yaml:
        fail("skills/deslop/agents/openai.yaml must disable implicit invocation")

    expected_payload = {
        "SKILL.md",
        "LICENSE.txt",
        "agents/openai.yaml",
        *required_references,
    }
    actual_payload = {
        path.relative_to(SKILL_ROOT).as_posix()
        for path in SKILL_ROOT.rglob("*")
        if path.is_file()
    }
    if actual_payload != expected_payload:
        fail(
            "runtime Skill payload differs from the allowed file set: "
            f"extra={sorted(actual_payload - expected_payload)} "
            f"missing={sorted(expected_payload - actual_payload)}"
        )

    wrapper = ROOT / "scripts" / "run_agent_skill_eval.py"
    wrapper_text = wrapper.read_text()
    if 'EXPECTED_VERSION = "0.7.0"' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must pin version 0.7.0")
    if 'CODEX_SKILL_PATH = ".agents/skills"' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must use .agents/skills")
    if 'command in {"run", "self-test"}' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must expose self-test")
    if 'AB_ORDER = "deterministic-counterbalanced"' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must counterbalance A/B order")

    exporter = ROOT / "scripts" / "export_results.py"
    if not exporter.is_file():
        fail("sanitized result exporter is missing")


def validate_eval_case(case: dict[str, object], seen_ids: set[str]) -> None:
    case_id = case.get("id")
    if not isinstance(case_id, str) or not case_id:
        fail("every eval requires a non-empty string id")
    if case_id in seen_ids:
        fail(f"duplicate eval id: {case_id}")
    if case_id != "mode-default-audit" and not CASE_ID.fullmatch(case_id):
        fail(f"eval id must be neutral: {case_id}")
    seen_ids.add(case_id)

    if case.get("force_skill_invocation") is not True:
        fail(f"{case_id}: explicit-only skill must be force-invoked")
    if case.get("side_effect_level") != "local-only":
        fail(f"{case_id}: fixtures must remain local-only")
    side_effect_contract = case.get("side_effect_contract")
    if not isinstance(side_effect_contract, dict):
        fail(f"{case_id}: missing side_effect_contract")
    if set(side_effect_contract) != SIDE_EFFECT_CONTRACT_KEYS:
        fail(f"{case_id}: incomplete side_effect_contract")
    expected_worktree_changes = case_id != "mode-default-audit"
    expected_contract = {
        key: expected_worktree_changes if key == "allow_worktree_changes" else False
        for key in SIDE_EFFECT_CONTRACT_KEYS
    }
    if side_effect_contract != expected_contract:
        fail(f"{case_id}: unexpected side_effect_contract")
    if case.get("assertions") != []:
        fail(f"{case_id}: visible assertions would leak adjudication; use the hidden hook")

    prompt = case.get("prompt")
    if not isinstance(prompt, str):
        fail(f"{case_id}: prompt must be a string")
    if "$deslop" in prompt:
        fail(f"{case_id}: prompt must not contaminate the without-skill baseline")
    if case_id != "mode-default-audit" and "apply" not in prompt.lower():
        fail(f"{case_id}: semantic cases require explicit apply authorization")
    if case_id == "mode-default-audit" and "apply" in prompt.lower():
        fail("default audit control must not authorize apply mode")

    files = case.get("files")
    if not isinstance(files, list) or not files:
        fail(f"{case_id}: missing fixture files")
    for file_name in files:
        if not isinstance(file_name, str):
            fail(f"{case_id}: fixture path must be a string")
        fixture_path = PurePosixPath(file_name)
        if fixture_path.is_absolute() or ".." in fixture_path.parts:
            fail(f"{case_id}: unsafe fixture path {file_name}")
        if not (ARCHIVE_ROOT / file_name).is_file():
            fail(f"{case_id}: missing fixture {file_name}")
        if "adjudication" in file_name or "grade_case" in file_name:
            fail(f"{case_id}: hidden adjudication leaked into the agent workspace")


def load_adjudication() -> tuple[dict[str, dict[str, object]], int, int]:
    document = json.loads(ADJUDICATION_PATH.read_text())
    if document.get("schema") != "deslop-adjudication-v1":
        fail("unexpected adjudication schema")
    if document.get("corpus_role") != "development":
        fail("public corpus must be labeled as development data")
    if document.get("corpus_version") != "dev-v1":
        fail("unexpected development corpus version")
    expected_fixture_count = document.get("expected_fixture_count")
    expected_baseline_tests = document.get("expected_baseline_tests")
    if not isinstance(expected_fixture_count, int) or expected_fixture_count < 1:
        fail("adjudication must declare expected_fixture_count")
    if not isinstance(expected_baseline_tests, int) or expected_baseline_tests < 1:
        fail("adjudication must declare expected_baseline_tests")
    cases = document.get("cases")
    if not isinstance(cases, list):
        fail("adjudication cases must be a list")
    indexed: dict[str, dict[str, object]] = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            fail("invalid adjudication case")
        case_id = case["id"]
        if case_id in indexed:
            fail(f"duplicate adjudication id: {case_id}")
        if case.get("expected") not in {"simplify", "preserve"}:
            fail(f"{case_id}: invalid adjudication expectation")
        if case.get("evidence") not in {"confirmed_change", "confirmed_boundary"}:
            fail(f"{case_id}: unconfirmed candidate cannot enter the scored corpus")
        indexed[case_id] = case
    return indexed, expected_fixture_count, expected_baseline_tests


def run_tests(workspace: Path, label: str) -> int:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v"],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        fail(f"tests failed: {label}")
    for line in result.stderr.splitlines():
        if line.startswith("Ran ") and " test" in line:
            return int(line.split()[1])
    fail(f"test runner did not report a count: {label}")


def run_baseline_tests() -> tuple[int, int]:
    fixture_root = ARCHIVE_ROOT / "files"
    case_dirs = sorted(path for path in fixture_root.iterdir() if CASE_ID.fullmatch(path.name))
    total_tests = sum(run_tests(case_dir, f"baseline {case_dir.name}") for case_dir in case_dirs)
    return len(case_dirs), total_tests


def run_grader(
    case_id: str,
    workspace: Path,
    extra_environment: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    environment = os.environ.copy()
    for name in (
        "ASE_AGENT",
        "ASE_WITH_SKILL",
        "ASE_SKILL_HASH",
        "ASE_RUN_META_PATH",
        "ASE_OUTPUT_DIR",
    ):
        environment.pop(name, None)
    environment["ASE_EVAL_ID"] = case_id
    environment["ASE_WORKSPACE_PATH"] = str(workspace)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.update(extra_environment or {})
    result = subprocess.run(
        [sys.executable, str(ARCHIVE_ROOT / "grade_case.py")],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        fail(f"hidden grader crashed for {case_id}: {result.stderr.strip()}")
    rows = json.loads(result.stdout)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        fail(f"hidden grader returned invalid rows for {case_id}")
    return rows


def result_with_prefix(rows: list[dict[str, object]], prefix: str) -> dict[str, object]:
    for row in rows:
        if str(row.get("text", "")).startswith(prefix):
            return row
    fail(f"hidden grader omitted result: {prefix}")


def materialize_calibration(case_id: str, expected: object, destination: Path) -> Path:
    state_name = "golden_after" if expected == "simplify" else "destructive_mutant"
    overlay = CALIBRATION_ROOT / case_id / state_name
    overlay_files = sorted(path for path in overlay.rglob("*") if path.is_file())
    if not overlay_files:
        fail(f"{case_id}: missing {state_name} calibration overlay")
    return materialize_overlay(case_id, state_name, destination)


def materialize_overlay(case_id: str, state_name: str, destination: Path) -> Path:
    fixture = ARCHIVE_ROOT / "files" / case_id
    overlay = CALIBRATION_ROOT / case_id / state_name
    workspace = destination / case_id
    shutil.copytree(fixture, workspace)
    for path in sorted(path for path in overlay.rglob("*") if path.is_file()):
        relative = path.relative_to(overlay)
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return workspace


def run_hidden_grader_calibration(adjudication: dict[str, dict[str, object]]) -> None:
    for case_id, case in sorted(adjudication.items()):
        before_rows = run_grader(case_id, ARCHIVE_ROOT / "files" / case_id)
        before_passed = bool(before_rows[0]["passed"])
        before_tests = bool(result_with_prefix(before_rows, "remaining unittest suite")["passed"])
        before_budget = bool(result_with_prefix(before_rows, "negative-change budget")["passed"])
        if not before_tests:
            fail(f"{case_id}: before-state remaining tests must pass")
        if not before_budget:
            fail(f"{case_id}: unchanged fixture exceeds the negative-change budget")

        with tempfile.TemporaryDirectory() as directory:
            calibrated_workspace = materialize_calibration(case_id, case["expected"], Path(directory))
            calibrated_rows = run_grader(case_id, calibrated_workspace)
        calibrated_passed = bool(calibrated_rows[0]["passed"])
        calibrated_tests = bool(
            result_with_prefix(calibrated_rows, "remaining unittest suite")["passed"]
        )
        calibrated_budget = bool(
            result_with_prefix(calibrated_rows, "negative-change budget")["passed"]
        )
        if not calibrated_budget:
            fail(f"{case_id}: calibration state exceeds the negative-change budget")

        if case["expected"] == "simplify":
            if before_passed:
                fail(f"{case_id}: simplify before-state must fail hidden adjudication")
            if not calibrated_passed:
                fail(f"{case_id}: golden_after must pass hidden adjudication")
            if not calibrated_tests:
                fail(f"{case_id}: golden_after remaining tests must pass")
        else:
            if not before_passed:
                fail(f"{case_id}: preserve before-state must pass hidden adjudication")
            if calibrated_passed:
                fail(f"{case_id}: destructive_mutant must fail hidden adjudication")



def run_alternate_valid_calibration(adjudication: dict[str, dict[str, object]]) -> int:
    count = 0
    for case_id, case in sorted(adjudication.items()):
        alternate_root = CALIBRATION_ROOT / case_id / "alternate_valid"
        if not alternate_root.is_dir():
            continue
        if case["expected"] != "simplify":
            fail(f"{case_id}: alternate_valid currently belongs only to simplify cases")
        with tempfile.TemporaryDirectory() as directory:
            workspace = materialize_overlay(case_id, "alternate_valid", Path(directory))
            rows = run_grader(case_id, workspace)
        if not rows[0]["passed"]:
            fail(f"{case_id}: alternate_valid must pass hidden adjudication")
        if not result_with_prefix(rows, "remaining unittest suite").get("passed"):
            fail(f"{case_id}: alternate_valid remaining tests must pass")
        if not result_with_prefix(rows, "negative-change budget").get("passed"):
            fail(f"{case_id}: alternate_valid exceeds the negative-change budget")
        count += 1
    if count < 1:
        fail("at least one alternate_valid calibration is required")
    return count


def run_c01a_diagnostics_calibration() -> None:
    expected_states = {
        "before": {
            "first_record_removed": False,
            "digest_helper_removed": False,
            "hashlib_dependency_removed": False,
            "load_episode_preserved": True,
        },
        "golden_after": {
            "first_record_removed": True,
            "digest_helper_removed": True,
            "hashlib_dependency_removed": True,
            "load_episode_preserved": True,
        },
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspaces = {
            "before": ARCHIVE_ROOT / "files" / "c01a",
            "golden_after": materialize_overlay("c01a", "golden_after", root),
        }
        for state, workspace in workspaces.items():
            output_dir = root / f"{state}-output"
            output_dir.mkdir()
            rows = run_grader("c01a", workspace, {"ASE_OUTPUT_DIR": str(output_dir)})
            diagnostics = json.loads((output_dir / "diagnostics.json").read_text())
            if diagnostics.get("details") != expected_states[state]:
                fail(f"c01a {state} diagnostics do not match the calibrated state")
            if len(rows) != 3:
                fail("c01a diagnostics changed scored assertion count")


def run_audit_calibration() -> None:
    fixture = ARCHIVE_ROOT / "files" / "c01a"
    unchanged_rows = run_grader("mode-default-audit", fixture)
    if not unchanged_rows[0]["passed"]:
        fail("default audit hidden check does not pass on unchanged input")

    mutations = {
        "added file": lambda workspace: (workspace / "audit-report.md").write_text("report\n"),
        "modified file": lambda workspace: (workspace / "app.py").write_text("modified\n"),
        "deleted file": lambda workspace: (workspace / "test_app.py").unlink(),
    }
    for label, mutate in mutations.items():
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "audit"
            shutil.copytree(fixture, workspace)
            mutate(workspace)
            rows = run_grader("mode-default-audit", workspace)
        if rows[0]["passed"]:
            fail(f"default audit accepted an {label}")


def run_remaining_tests_calibration() -> None:
    fixture = ARCHIVE_ROOT / "files" / "c01b"
    mutations = {
        "failing test": lambda workspace: (workspace / "test_app.py").write_text(
            "import unittest\n\n"
            "class BrokenTests(unittest.TestCase):\n"
            "    def test_broken(self):\n"
            "        self.fail('broken')\n"
        ),
        "zero tests": lambda workspace: (workspace / "test_app.py").unlink(),
    }
    for label, mutate in mutations.items():
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "remaining-tests"
            shutil.copytree(fixture, workspace)
            mutate(workspace)
            rows = run_grader("c01b", workspace)
        if not rows[0]["passed"]:
            fail(f"{label} calibration no longer isolates the remaining-test gate")
        if result_with_prefix(rows, "remaining unittest suite").get("passed") is not False:
            fail(f"remaining-test gate accepted {label}")


def run_negative_budget_calibration() -> None:
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "c01b"
        shutil.copytree(ARCHIVE_ROOT / "files" / "c01b", workspace)
        installed_skill = workspace / ".fake" / "skills" / "deslop" / "SKILL.md"
        installed_skill.parent.mkdir(parents=True)
        installed_skill.write_text("---\nname: deslop\ndescription: smoke fixture\n---\n")
        installed_rows = run_grader(
            "c01b",
            workspace,
            {"ASE_AGENT": "fake", "ASE_WITH_SKILL": "1"},
        )
        if result_with_prefix(installed_rows, "negative-change budget").get("passed") is not True:
            fail("negative-change budget counted the harness-installed Skill payload")
        shutil.rmtree(workspace / ".fake")

        nested_files = [
            workspace / "new_framework" / "validator.py",
            workspace / ".agents" / "new_framework" / "validator.py",
        ]
        for nested_file in nested_files:
            nested_file.parent.mkdir(parents=True, exist_ok=True)
            nested_file.write_text("class Validator:\n    pass\n")
        rows = run_grader("c01b", workspace)
    budget = result_with_prefix(rows, "negative-change budget")
    evidence = str(budget.get("evidence", ""))
    if budget.get("passed") is not False:
        fail("negative-change budget accepted a nested new package")
    if (
        "new_framework/validator.py" not in evidence
        or ".agents/new_framework/validator.py" not in evidence
        or "structural_delta=" not in evidence
    ):
        fail("negative-change budget did not report recursive file and AST evidence")

    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "c01b"
        shutil.copytree(ARCHIVE_ROOT / "files" / "c01b", workspace)
        (workspace / "test_app.py").write_text("def broken(:\n")
        rows = run_grader("c01b", workspace)
    budget = result_with_prefix(rows, "negative-change budget")
    if budget.get("passed") is not False:
        fail("negative-change budget accepted a Python syntax error")
    if '"syntax_errors":1' not in str(budget.get("evidence", "")):
        fail("negative-change budget did not report the Python syntax error")


def run_skill_discovery_calibration() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "audit"
        shutil.copytree(ARCHIVE_ROOT / "files" / "c01a", workspace)
        installed_skill = workspace / ".agents" / "skills" / "deslop"
        installed_skill.mkdir(parents=True)
        shutil.copytree(SKILL_ROOT, installed_skill, dirs_exist_ok=True)
        expected_hash = skill_content_hash(SKILL_ROOT)
        metadata_path = root / "run_meta.json"
        metadata_path.write_text("{}")
        rows = run_grader(
            "mode-default-audit",
            workspace,
            {
                "ASE_AGENT": "codex",
                "ASE_WITH_SKILL": "1",
                "ASE_SKILL_HASH": expected_hash,
                "ASE_RUN_META_PATH": str(metadata_path),
            },
        )

        if len(rows) != 1 or not rows[0]["passed"]:
            fail("successful Skill discovery changed audit scoring")
        if any(str(row.get("text", "")).startswith("Codex skill discovery") for row in rows):
            fail("successful Skill discovery emitted a scored assertion")
        metadata = json.loads(metadata_path.read_text())
        skill_discovery = metadata.get("skill_discovery", {})
        if skill_discovery.get("verified") is not True:
            fail("run metadata did not mark Codex Skill discovery as verified")
        if skill_discovery.get("path") != ".agents/skills/deslop":
            fail("run metadata did not record the canonical Codex Skill path")
        if skill_discovery.get("content_hash") != expected_hash:
            fail("run metadata did not record the installed Skill content hash")

        metadata_path.write_text("{}")
        failed_rows = run_grader(
            "mode-default-audit",
            workspace,
            {
                "ASE_AGENT": "codex",
                "ASE_WITH_SKILL": "1",
                "ASE_SKILL_HASH": "wrong-hash",
                "ASE_RUN_META_PATH": str(metadata_path),
            },
        )
        discovery_failure = result_with_prefix(failed_rows, "Codex skill discovery")
        if discovery_failure.get("passed") is not False:
            fail("failed Skill discovery did not emit a hard-fail assertion")


def main() -> None:
    validate_skill()
    suite = json.loads(EVALS_PATH.read_text())
    if suite.get("skill_name") != "deslop":
        fail("eval suite skill_name must be deslop")
    evals = suite.get("evals")
    if not isinstance(evals, list):
        fail("evals must be a list")

    seen_ids: set[str] = set()
    for case in evals:
        if not isinstance(case, dict):
            fail("each eval must be an object")
        validate_eval_case(case, seen_ids)

    adjudication, expected_fixture_count, expected_baseline_tests = load_adjudication()
    semantic_ids = seen_ids - {"mode-default-audit"}
    if semantic_ids != set(adjudication):
        fail("eval and adjudication case ids differ")
    simplify_count = sum(case["expected"] == "simplify" for case in adjudication.values())
    preserve_count = sum(case["expected"] == "preserve" for case in adjudication.values())
    if (simplify_count, preserve_count) != (10, 10):
        fail(f"expected 10 simplify and 10 preserve cases, got {simplify_count} and {preserve_count}")

    fixture_count, test_count = run_baseline_tests()
    if fixture_count != expected_fixture_count:
        fail(f"expected {expected_fixture_count} fixture directories, got {fixture_count}")
    if test_count != expected_baseline_tests:
        fail(f"expected {expected_baseline_tests} baseline tests, got {test_count}")
    run_hidden_grader_calibration(adjudication)
    alternate_count = run_alternate_valid_calibration(adjudication)
    run_c01a_diagnostics_calibration()
    run_audit_calibration()
    run_remaining_tests_calibration()
    run_negative_budget_calibration()
    run_skill_discovery_calibration()

    print(
        f"Validated archived dev-v1: {len(evals)} evals: {simplify_count} confirmed changes, "
        f"{preserve_count} confirmed boundaries, 1 authorization control; "
        f"{fixture_count} fixtures and {test_count} baseline tests passed; "
        "hidden grader calibration passed 20/20 positive + 20/20 negative states; "
        f"{alternate_count} alternate valid states passed; non-scored c01a diagnostics, "
        "zero-mutation audit, recursive and syntax-safe negative-change, remaining-test, "
        "score-neutral skill-discovery, and deterministic A/B requirements passed."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
