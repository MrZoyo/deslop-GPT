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
EVALS_PATH = ROOT / "evals" / "evals.json"
ADJUDICATION_PATH = ROOT / "evals" / "adjudication.json"
CALIBRATION_ROOT = ROOT / "evals" / "calibration"
CASE_ID = re.compile(r"c(0[1-9]|10)[ab]")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_skill() -> None:
    skill_text = (ROOT / "SKILL.md").read_text()
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
    }
    for reference in required_references:
        if reference not in skill_text or not (ROOT / reference).is_file():
            fail(f"SKILL.md does not route to {reference}")

    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text()
    if "allow_implicit_invocation: false" not in openai_yaml:
        fail("agents/openai.yaml must disable implicit invocation")

    wrapper = ROOT / "scripts" / "run_agent_skill_eval.py"
    wrapper_text = wrapper.read_text()
    if 'EXPECTED_VERSION = "0.7.0"' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must pin version 0.7.0")
    if 'CODEX_SKILL_PATH = ".agents/skills"' not in wrapper_text:
        fail("agent-skill-eval compatibility wrapper must use .agents/skills")


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
        if not (ROOT / "evals" / file_name).is_file():
            fail(f"{case_id}: missing fixture {file_name}")
        if "adjudication" in file_name or "grade_case" in file_name:
            fail(f"{case_id}: hidden adjudication leaked into the agent workspace")


def load_adjudication() -> tuple[dict[str, dict[str, object]], int, int]:
    document = json.loads(ADJUDICATION_PATH.read_text())
    if document.get("schema") != "deslop-adjudication-v1":
        fail("unexpected adjudication schema")
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
    fixture_root = ROOT / "evals" / "files"
    case_dirs = sorted(path for path in fixture_root.iterdir() if CASE_ID.fullmatch(path.name))
    total_tests = sum(run_tests(case_dir, f"baseline {case_dir.name}") for case_dir in case_dirs)
    return len(case_dirs), total_tests


def run_grader(
    case_id: str,
    workspace: Path,
    extra_environment: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    environment = os.environ.copy()
    for name in ("ASE_AGENT", "ASE_WITH_SKILL", "ASE_SKILL_HASH", "ASE_RUN_META_PATH"):
        environment.pop(name, None)
    environment["ASE_EVAL_ID"] = case_id
    environment["ASE_WORKSPACE_PATH"] = str(workspace)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.update(extra_environment or {})
    result = subprocess.run(
        [sys.executable, str(ROOT / "evals" / "grade_case.py")],
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
    fixture = ROOT / "evals" / "files" / case_id
    state_name = "golden_after" if expected == "simplify" else "destructive_mutant"
    overlay = CALIBRATION_ROOT / case_id / state_name
    overlay_files = sorted(path for path in overlay.rglob("*") if path.is_file())
    if not overlay_files:
        fail(f"{case_id}: missing {state_name} calibration overlay")

    workspace = destination / case_id
    shutil.copytree(fixture, workspace)
    for path in overlay_files:
        relative = path.relative_to(overlay)
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return workspace


def run_hidden_grader_calibration(adjudication: dict[str, dict[str, object]]) -> None:
    for case_id, case in sorted(adjudication.items()):
        before_rows = run_grader(case_id, ROOT / "evals" / "files" / case_id)
        before_passed = bool(before_rows[0]["passed"])
        before_budget = bool(result_with_prefix(before_rows, "negative-change budget")["passed"])
        if not before_budget:
            fail(f"{case_id}: unchanged fixture exceeds the negative-change budget")

        with tempfile.TemporaryDirectory() as directory:
            calibrated_workspace = materialize_calibration(case_id, case["expected"], Path(directory))
            calibrated_rows = run_grader(case_id, calibrated_workspace)
            if case["expected"] == "simplify":
                run_tests(calibrated_workspace, f"{case_id} golden_after")
        calibrated_passed = bool(calibrated_rows[0]["passed"])
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
        else:
            if not before_passed:
                fail(f"{case_id}: preserve before-state must pass hidden adjudication")
            if calibrated_passed:
                fail(f"{case_id}: destructive_mutant must fail hidden adjudication")

    audit_rows = run_grader("mode-default-audit", ROOT / "evals" / "files" / "c01a")
    if not audit_rows[0]["passed"]:
        fail("default audit hidden check does not pass on unchanged input")


def run_negative_budget_calibration() -> None:
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "c01b"
        shutil.copytree(ROOT / "evals" / "files" / "c01b", workspace)
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


def run_skill_discovery_calibration() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "c01b"
        shutil.copytree(ROOT / "evals" / "files" / "c01b", workspace)
        installed_skill = workspace / ".agents" / "skills" / "deslop"
        installed_skill.mkdir(parents=True)
        skill_bytes = (ROOT / "SKILL.md").read_bytes()
        (installed_skill / "SKILL.md").write_bytes(skill_bytes)

        digest = hashlib.sha256()
        digest.update(b"SKILL.md\0")
        digest.update(skill_bytes)
        digest.update(b"\0")
        expected_hash = digest.hexdigest()
        metadata_path = root / "run_meta.json"
        metadata_path.write_text("{}")
        rows = run_grader(
            "c01b",
            workspace,
            {
                "ASE_AGENT": "codex",
                "ASE_WITH_SKILL": "1",
                "ASE_SKILL_HASH": expected_hash,
                "ASE_RUN_META_PATH": str(metadata_path),
            },
        )

        discovery = result_with_prefix(rows, "Codex skill discovery")
        if discovery.get("passed") is not True:
            fail(f"Codex skill-discovery calibration failed: {discovery.get('evidence')}")
        if result_with_prefix(rows, "negative-change budget").get("passed") is not True:
            fail("negative-change budget counted the canonical Codex Skill payload")
        metadata = json.loads(metadata_path.read_text())
        skill_discovery = metadata.get("skill_discovery", {})
        if skill_discovery.get("path") != ".agents/skills/deslop":
            fail("run metadata did not record the canonical Codex Skill path")
        if skill_discovery.get("content_hash") != expected_hash:
            fail("run metadata did not record the installed Skill content hash")


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
    run_negative_budget_calibration()
    run_skill_discovery_calibration()

    print(
        f"Validated {len(evals)} evals: {simplify_count} confirmed changes, "
        f"{preserve_count} confirmed boundaries, 1 authorization control; "
        f"{fixture_count} fixtures and {test_count} baseline tests passed; "
        "hidden grader calibration passed 20/20 positive + 20/20 negative states; "
        "recursive negative-change and canonical skill-discovery calibrations passed."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
