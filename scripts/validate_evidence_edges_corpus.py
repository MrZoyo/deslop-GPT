#!/usr/bin/env python3
"""Dependency-free validation for the dev-v3 evidence-edge draft."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath


sys.dont_write_bytecode = True

REPOSITORY = Path(__file__).resolve().parents[1]
CORPUS = REPOSITORY / "evals" / "dev-v3-evidence-edges"
EVALS = CORPUS / "evals.json"
ADJUDICATION = CORPUS / "adjudication.json"
EVIDENCE_BANK = CORPUS / "evidence-bank.json"
REVISION = "dev-v3-evidence-edges-draft1"
CASE_IDS = {
    "r01a",
    "r01b",
    "r02a",
    "r02b",
    "h01a",
    "h01b",
    "h02a",
    "h02b",
    "v03a",
    "v03b",
    "s01a",
    "s01b",
    "s02a",
    "s02b",
}
PAIR_IDS = {"r01", "r02", "h01", "h02", "v03", "s01", "s02"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_grader():
    path = CORPUS / "grade_evidence_edges.py"
    spec = importlib.util.spec_from_file_location("evidence_edges_grader", path)
    if spec is None or spec.loader is None:
        fail("could not load evidence-edge grader")
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    return grader


def materialize(case_id: str, state: str, root: Path) -> Path:
    workspace = root / f"{case_id}-{state}"
    shutil.copytree(CORPUS / "files" / case_id, workspace)
    overlay = CORPUS / "calibration" / case_id / state
    if overlay.is_dir():
        for path in overlay.rglob("*"):
            if path.is_file():
                target = workspace / path.relative_to(overlay)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    return workspace


def require_tests(grader, workspace: Path, label: str) -> None:
    result = grader.run_tests(workspace)
    if not result["passed"]:
        fail(f"{label}: tests failed or zero tests were discovered: {result['output']}")


def expect_failure(call, label: str) -> None:
    try:
        call()
    except Exception:
        return
    fail(f"{label}: expected hidden failure but call passed")


def validate_evidence_bank(bank: dict) -> None:
    if bank.get("schema") != "deslop-field-evidence-v1":
        fail("unexpected evidence-bank schema")
    observations = bank.get("observations")
    if not isinstance(observations, list) or len(observations) != 19:
        fail("evidence bank must contain 19 observations")
    expected_ids = {f"p{index:02d}" for index in range(1, 20)}
    if {item.get("id") for item in observations} != expected_ids:
        fail("evidence bank observation IDs drifted")
    allowed_coverage = {"candidate", "existing", "new"}
    preservation_roots = bank.get("preservation_roots")
    if not isinstance(preservation_roots, list) or {
        root.get("category") for root in preservation_roots
    } != {
        "safety_and_task_result",
        "persistence_and_external_protocol",
        "hardware_calibration_and_numerics",
    }:
        fail("evidence bank preservation roots drifted")
    if any(
        not isinstance(root.get("examples"), list) or len(root["examples"]) < 5
        for root in preservation_roots
    ):
        fail("each preservation-root group needs concrete examples")
    covered_new_pairs = set()
    coverage_counts = {kind: 0 for kind in allowed_coverage}
    for item in observations:
        for field in ("title", "cluster", "positive", "negative", "independent_oracle"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                fail(f"{item.get('id')}: missing evidence field {field}")
        coverage = item.get("coverage")
        if not isinstance(coverage, dict) or coverage.get("kind") not in allowed_coverage:
            fail(f"{item['id']}: invalid coverage record")
        coverage_counts[coverage["kind"]] += 1
        pairs = coverage.get("pairs")
        if not isinstance(pairs, list) or not all(isinstance(pair, str) for pair in pairs):
            fail(f"{item['id']}: invalid coverage pairs")
        if coverage["kind"] == "new":
            covered_new_pairs.update(pairs)
    if covered_new_pairs != PAIR_IDS:
        fail(f"evidence bank does not map every executable pair: {sorted(covered_new_pairs)}")
    if coverage_counts != {"candidate": 5, "existing": 5, "new": 9}:
        fail(f"evidence-bank coverage counts drifted: {coverage_counts}")


def validate_manifest(evals: dict, adjudication: dict) -> None:
    if evals.get("schema") != "deslop-evals-v3-evidence-edges":
        fail("unexpected evidence-edge eval schema")
    if evals.get("skill_name") != "deslop":
        fail("evidence-edge suite must target deslop")
    if evals.get("corpus_version") != "dev-v3-evidence-edges":
        fail("unexpected evidence-edge corpus version")
    if evals.get("corpus_revision") != REVISION:
        fail("eval manifest revision drifted")
    if adjudication.get("corpus_revision") != REVISION or adjudication.get("status") != "draft":
        fail("adjudication must identify the draft revision")
    if set(adjudication.get("scope", [])) != {
        "production_reachability",
        "test_hermeticity",
        "artifact_authority",
        "schema_contract",
    }:
        fail("evidence-edge scope drifted")
    if adjudication.get("negative_change_budget") != {
        "new_files_max": 0,
        "test_count_growth_max": 0,
        "new_external_dependencies_max": 0,
        "abstraction_growth_max": 0,
        "syntax_errors_max": 0,
        "positive_python_loc_growth_max": {
            "simplify": 4,
            "repair": 12,
            "preserve": 4,
        },
    }:
        fail("negative-change limits drifted")

    cases = evals.get("evals")
    adjudicated = adjudication.get("cases")
    if not isinstance(cases, list) or {case.get("id") for case in cases} != CASE_IDS:
        fail("eval manifest case IDs drifted")
    if not isinstance(adjudicated, list) or {case.get("id") for case in adjudicated} != CASE_IDS:
        fail("adjudication case IDs drifted")

    pairs = {}
    for case in adjudicated:
        pair = case.get("pair")
        pairs.setdefault(pair, []).append(case)
        if case.get("expected") not in {"simplify", "repair", "preserve"}:
            fail(f"{case['id']}: invalid expected action")
        if case.get("category") not in adjudication["scope"]:
            fail(f"{case['id']}: invalid category")
        if not case.get("target") or not case.get("evidence_root"):
            fail(f"{case['id']}: missing hidden adjudication evidence")
    if set(pairs) != PAIR_IDS:
        fail("adjudication pair IDs drifted")
    for pair, members in pairs.items():
        if len(members) != 2:
            fail(f"{pair}: pair must contain two cases")
        a = next((case for case in members if case["id"].endswith("a")), None)
        b = next((case for case in members if case["id"].endswith("b")), None)
        if a is None or b is None or a["expected"] not in {"simplify", "repair"} or b["expected"] != "preserve":
            fail(f"{pair}: pair must contain one positive action and one preservation case")

    for case in cases:
        case_id = case["id"]
        if case.get("force_skill_invocation") is not True or case.get("assertions") != []:
            fail(f"{case_id}: hidden grading must be forced")
        prompt = case.get("prompt", "")
        if "$deslop" in prompt or "apply" not in prompt.casefold():
            fail(f"{case_id}: prompt must authorize apply without leaking invocation syntax")
        files = case.get("files")
        if not isinstance(files, list) or not files:
            fail(f"{case_id}: missing fixture files")
        fixture_root = CORPUS / "files" / case_id
        expected_files = {
            path.relative_to(CORPUS).as_posix()
            for path in fixture_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }
        if set(files) != expected_files:
            fail(f"{case_id}: manifest must include the complete fixture")
        for file_name in files:
            path = PurePosixPath(file_name)
            if path.is_absolute() or ".." in path.parts or not (CORPUS / path).is_file():
                fail(f"{case_id}: unsafe or missing fixture path {file_name}")
            if "calibration" in path.parts or path.name.startswith("grade_"):
                fail(f"{case_id}: hidden material leaked into fixture")


def validate_calibration(grader, adjudication: dict) -> None:
    alternate_categories = set()
    insufficient_categories = set()
    for case in adjudication["cases"]:
        case_id = case["id"]
        action = case["expected"]
        fixture = CORPUS / "files" / case_id
        require_tests(grader, fixture, f"{case_id} before")
        try:
            grader.case_contract(case_id, fixture)
        except Exception as error:
            fail(f"{case_id}: baseline current behavior failed: {error}")
        budget_passed, budget_evidence = grader.negative_change_budget(fixture, fixture, action)
        if not budget_passed:
            fail(f"{case_id}: unchanged fixture exceeds budget: {budget_evidence}")

        if action in {"simplify", "repair"}:
            expect_failure(
                lambda case_id=case_id, fixture=fixture: grader.case_target(case_id, fixture),
                f"{case_id} before target",
            )
            golden = CORPUS / "calibration" / case_id / "golden_after"
            if not golden.is_dir():
                fail(f"{case_id}: missing golden_after")
            with tempfile.TemporaryDirectory() as directory:
                workspace = materialize(case_id, "golden_after", Path(directory))
                require_tests(grader, workspace, f"{case_id} golden_after")
                grader.case_contract(case_id, workspace)
                grader.case_target(case_id, workspace)
                budget_passed, budget_evidence = grader.negative_change_budget(
                    fixture, workspace, action
                )
                if not budget_passed:
                    fail(f"{case_id}: golden_after exceeds budget: {budget_evidence}")
        else:
            mutant = CORPUS / "calibration" / case_id / "destructive_mutant"
            if not mutant.is_dir():
                fail(f"{case_id}: missing destructive_mutant")
            with tempfile.TemporaryDirectory() as directory:
                workspace = materialize(case_id, "destructive_mutant", Path(directory))
                require_tests(grader, workspace, f"{case_id} destructive_mutant")
                expect_failure(
                    lambda case_id=case_id, workspace=workspace: grader.case_contract(
                        case_id, workspace
                    ),
                    f"{case_id} destructive_mutant contract",
                )

        alternate = CORPUS / "calibration" / case_id / "alternate_valid"
        if alternate.is_dir():
            with tempfile.TemporaryDirectory() as directory:
                workspace = materialize(case_id, "alternate_valid", Path(directory))
                require_tests(grader, workspace, f"{case_id} alternate_valid")
                grader.case_contract(case_id, workspace)
                if case_id.endswith("a"):
                    grader.case_target(case_id, workspace)
                budget_passed, budget_evidence = grader.negative_change_budget(
                    fixture, workspace, action
                )
                if not budget_passed:
                    fail(f"{case_id}: alternate_valid exceeds budget: {budget_evidence}")
            alternate_categories.add(case["category"])

        insufficient = CORPUS / "calibration" / case_id / "insufficient_cleanup"
        if insufficient.is_dir():
            if action != "simplify":
                fail(f"{case_id}: only simplify cases may have insufficient_cleanup")
            with tempfile.TemporaryDirectory() as directory:
                workspace = materialize(case_id, "insufficient_cleanup", Path(directory))
                require_tests(grader, workspace, f"{case_id} insufficient_cleanup")
                grader.case_contract(case_id, workspace)
                expect_failure(
                    lambda case_id=case_id, workspace=workspace: grader.case_target(
                        case_id, workspace
                    ),
                    f"{case_id} insufficient_cleanup target",
                )
                before = grader.source_metrics(fixture)
                after = grader.source_metrics(workspace)
                if not (
                    after["production_loc"] < before["production_loc"]
                    or after["test_loc"] < before["test_loc"]
                    or after["test_count"] < before["test_count"]
                ):
                    fail(f"{case_id}: insufficient cleanup removed no surface")
            insufficient_categories.add(case["category"])

    if alternate_categories != set(adjudication["scope"]):
        fail(f"every category needs an alternate-valid calibration: {sorted(alternate_categories)}")
    simplify_categories = {
        case["category"] for case in adjudication["cases"] if case["expected"] == "simplify"
    }
    if insufficient_categories != simplify_categories:
        fail(
            "every category with a simplify case needs insufficient cleanup: "
            f"{sorted(insufficient_categories)}"
        )


def validate_negative_change_gate(grader) -> None:
    fixture = CORPUS / "files" / "r01b"

    def reject(label: str, relative: str, content: str, expected: str, append: bool = True) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / label
            shutil.copytree(fixture, workspace)
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if append:
                path.write_text(path.read_text() + content)
            else:
                path.write_text(content)
            passed, evidence = grader.negative_change_budget(fixture, workspace, "preserve")
            if passed or expected not in evidence:
                fail(f"negative-change gate accepted {label}: {evidence}")

    reject("new-file", "extra.txt", "new\n", "new files", append=False)
    reject(
        "new-test",
        "test_app.py",
        "\n\nclass AddedTests(unittest.TestCase):\n    def test_added(self):\n        self.assertTrue(True)\n",
        "new tests",
    )
    reject("dependency", "app.py", "\nimport pandas\n", "new external dependencies")
    reject("abstraction", "app.py", "\n\nclass CameraManager:\n    pass\n", "new abstractions")
    reject("syntax", "app.py", "\ndef broken(:\n", "Python syntax errors")
    reject(
        "loc-growth",
        "app.py",
        "\nEXTRA_1 = 1\nEXTRA_2 = 2\nEXTRA_3 = 3\nEXTRA_4 = 4\nEXTRA_5 = 5\n",
        "Python LOC growth",
    )


def main() -> None:
    evals = json.loads(EVALS.read_text())
    adjudication = json.loads(ADJUDICATION.read_text())
    bank = json.loads(EVIDENCE_BANK.read_text())
    validate_evidence_bank(bank)
    validate_manifest(evals, adjudication)
    grader = load_grader()
    validate_calibration(grader, adjudication)
    validate_negative_change_gate(grader)
    print(
        "Validated dev-v3-evidence-edges-draft1: 19 field observations "
        "(9 newly covered, 5 existing, 5 candidates), 7 executable pairs, "
        "golden/mutant polarity, alternate-valid states, "
        "insufficient-cleanup states, and negative-change gates."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"evidence-edge validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
