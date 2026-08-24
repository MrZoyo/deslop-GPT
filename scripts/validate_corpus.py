#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
EVALS_PATH = ROOT / "evals" / "evals.json"
ADJUDICATION_PATH = ROOT / "evals" / "adjudication.json"
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


def load_adjudication() -> dict[str, dict[str, object]]:
    document = json.loads(ADJUDICATION_PATH.read_text())
    if document.get("schema") != "deslop-adjudication-v1":
        fail("unexpected adjudication schema")
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
    return indexed


def run_baseline_tests() -> tuple[int, int]:
    fixture_root = ROOT / "evals" / "files"
    case_dirs = sorted(path for path in fixture_root.iterdir() if CASE_ID.fullmatch(path.name))
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    total_tests = 0
    for case_dir in case_dirs:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "-v"],
            cwd=case_dir,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            fail(f"baseline tests failed: {case_dir.name}")
        for line in result.stderr.splitlines():
            if line.startswith("Ran ") and " test" in line:
                total_tests += int(line.split()[1])
                break
    return len(case_dirs), total_tests


def run_hidden_grader_baseline(
    adjudication: dict[str, dict[str, object]],
) -> tuple[int, int]:
    simplify_rejected = 0
    preserve_passed = 0
    for case_id, case in sorted(adjudication.items()):
        environment = os.environ.copy()
        environment["ASE_EVAL_ID"] = case_id
        environment["ASE_WORKSPACE_PATH"] = str(ROOT / "evals" / "files" / case_id)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
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
        passed = bool(rows[0]["passed"])
        if case["expected"] == "simplify" and not passed:
            simplify_rejected += 1
        elif case["expected"] == "preserve" and passed:
            preserve_passed += 1

    environment = os.environ.copy()
    environment["ASE_EVAL_ID"] = "mode-default-audit"
    environment["ASE_WORKSPACE_PATH"] = str(ROOT / "evals" / "files" / "c01a")
    audit = subprocess.run(
        [sys.executable, str(ROOT / "evals" / "grade_case.py")],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if audit.returncode or not json.loads(audit.stdout)[0]["passed"]:
        fail("default audit hidden check does not pass on unchanged input")
    return simplify_rejected, preserve_passed


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

    adjudication = load_adjudication()
    semantic_ids = seen_ids - {"mode-default-audit"}
    if semantic_ids != set(adjudication):
        fail("eval and adjudication case ids differ")
    simplify_count = sum(case["expected"] == "simplify" for case in adjudication.values())
    preserve_count = sum(case["expected"] == "preserve" for case in adjudication.values())
    if (simplify_count, preserve_count) != (10, 10):
        fail(f"expected 10 simplify and 10 preserve cases, got {simplify_count} and {preserve_count}")

    fixture_count, test_count = run_baseline_tests()
    if fixture_count != 20:
        fail(f"expected 20 fixture directories, got {fixture_count}")
    simplify_rejected, preserve_passed = run_hidden_grader_baseline(adjudication)
    if simplify_rejected != 10 or preserve_passed != 10:
        fail(
            "hidden baseline polarity failed: "
            f"simplify={simplify_rejected}/10 preserve={preserve_passed}/10"
        )

    print(
        f"Validated {len(evals)} evals: {simplify_count} confirmed changes, "
        f"{preserve_count} confirmed boundaries, 1 authorization control; "
        f"{fixture_count} fixtures and {test_count} baseline tests passed; "
        "hidden grader polarity passed 10/10 + 10/10."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
