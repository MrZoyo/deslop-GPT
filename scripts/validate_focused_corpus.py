#!/usr/bin/env python3
"""Dependency-free validation for the focused dev-v2 corpus."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath


CORPUS = Path(__file__).resolve().parents[1] / "evals" / "dev-v2-focused"
EVALS = CORPUS / "evals.json"
MINI_EVALS = CORPUS / "mini-evals.json"
ADJUDICATION = CORPUS / "adjudication.json"
MINI_CALIBRATION = CORPUS / "mini-repo-calibration"
CORPUS_REVISION = "dev-v2-focused-rc5"
CASE_IDS = {"t01a", "t01b", "t02a", "t02b", "t03a", "t03b", "t04a", "t04b", "v01a", "v01b", "v02a", "v02b", "f01a", "f01b", "f02a", "f02b"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_grader():
    path = CORPUS / "grade_focused.py"
    spec = importlib.util.spec_from_file_location("focused_grader", path)
    if spec is None or spec.loader is None:
        fail("could not load focused grader")
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    return grader


def run_tests(grader, workspace: Path, label: str) -> None:
    result = grader.run_tests(workspace)
    if not result["passed"]:
        fail(f"{label}: baseline tests failed or reported zero tests: {result}")


def materialize(case_id: str, state: str, root: Path) -> Path:
    source = CORPUS / "files" / case_id
    workspace = root / f"{case_id}-{state}"
    shutil.copytree(source, workspace)
    overlay = CORPUS / "calibration" / case_id / state
    if overlay.is_dir():
        for path in overlay.rglob("*"):
            if not path.is_file():
                continue
            target = workspace / path.relative_to(overlay)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return workspace


def validate_manifest(evals: dict, mini_evals: dict, adjudication: dict) -> None:
    if evals.get("schema") != "deslop-evals-v2-focused":
        fail("unexpected focused eval schema")
    if evals.get("skill_name") != "deslop":
        fail("focused suite must target deslop")
    if evals.get("corpus_version") != "dev-v2-focused":
        fail("unexpected focused corpus version")
    if evals.get("corpus_revision") != CORPUS_REVISION:
        fail("unexpected focused corpus revision")
    if adjudication.get("corpus_revision") != CORPUS_REVISION:
        fail("adjudication does not identify the rc5 revision")
    cases = evals.get("evals")
    if not isinstance(cases, list) or {case.get("id") for case in cases} != CASE_IDS:
        fail("focused eval ids do not match the 16-case taxonomy")
    adjudication_cases = adjudication.get("cases")
    if not isinstance(adjudication_cases, list) or {case.get("id") for case in adjudication_cases} != CASE_IDS:
        fail("focused adjudication ids do not match eval ids")
    if adjudication.get("scope") != {"test_bloat": 4, "verification_theater": 2, "defensive_fallback_bloat": 2}:
        fail("focused category mix must remain 4/2/2 deletion cases")
    if adjudication.get("micro_reduction_targets") != {
        "test_bloat": {"test_count_max": 1},
        "verification_theater": {
            "checksum_mentions_max": 0,
            "local_verifier_functions_max": 0,
            "hash_operations_max": 0,
        },
        "defensive_fallback_bloat": {
            "branches_max": 0,
            "try_blocks_max": 0,
            "except_handlers_max": 0,
        },
    }:
        fail("focused micro reduction thresholds drifted")
    if adjudication.get("mini_reduction_targets") != {
        "test_bloat": {
            "test_count_fraction_max": "1/2",
            "test_loc_fraction_max": "1/2",
            "fixture_invocations_fraction_max": "1/2",
        },
        "verification_theater": {
            "local_verifier_functions_max": 0,
            "hash_operations_max": 1,
            "checksum_mentions_fraction_max": "1/2",
        },
        "defensive_fallback_bloat": {
            "try_blocks_max": 1,
            "catch_fallback_handlers_max": 0,
            "try_blocks_must_decrease": True,
            "except_handlers_must_decrease": True,
        },
    }:
        fail("focused mini-repository reduction thresholds drifted")
    if adjudication.get("negative_change_budget") != {
        "new_python_files_max": 0,
        "test_count_growth_max": 0,
        "positive_python_loc_growth_max": 4,
        "abstraction_growth_max": 0,
        "new_dependencies_max": 0,
        "category_target_growth_max": 0,
        "syntax_errors_max": 0,
    }:
        fail("focused negative-change budget drifted")

    indexed = {case["id"]: case for case in adjudication_cases}
    pairs = {}
    for case in adjudication_cases:
        pair = case.get("pair")
        pairs.setdefault(pair, []).append(case)
        if case.get("expected") not in {"simplify", "preserve"}:
            fail(f"{case['id']}: invalid expected action")
        if case.get("category") not in adjudication["scope"]:
            fail(f"{case['id']}: invalid focused category")
    for pair, members in pairs.items():
        if {member["expected"] for member in members} != {"simplify", "preserve"}:
            fail(f"{pair}: every deletion case needs a nearby preservation counterexample")
        if len(members) != 2:
            fail(f"{pair}: pair must contain exactly two cases")

    for case in cases:
        case_id = case["id"]
        if case.get("force_skill_invocation") is not True or case.get("assertions") != []:
            fail(f"{case_id}: focused cases must use explicit hidden grading")
        if "$deslop" in case.get("prompt", ""):
            fail(f"{case_id}: prompt leaks Skill invocation")
        if "apply" not in case.get("prompt", "").lower():
            fail(f"{case_id}: prompt must authorize a focused apply")
        files = case.get("files")
        if not isinstance(files, list) or not files:
            fail(f"{case_id}: missing files")
        for file_name in files:
            path = PurePosixPath(file_name)
            if path.is_absolute() or ".." in path.parts or not (CORPUS / file_name).is_file():
                fail(f"{case_id}: unsafe or missing fixture {file_name}")
            if "adjudication" in path.parts or "grade_focused" in path.parts:
                fail(f"{case_id}: hidden grader leaked into fixture")

    if len(indexed) != 16:
        fail("focused adjudication index is incomplete")
    alternate_counts = {category: 0 for category in adjudication["scope"]}
    for case in adjudication_cases:
        if (CORPUS / "calibration" / case["id"] / "alternate_valid").is_dir():
            alternate_counts[case["category"]] += 1
    if any(count < 2 for count in alternate_counts.values()):
        fail(f"each focused category needs at least two alternate_valid calibrations: {alternate_counts}")

    if mini_evals.get("schema") != "deslop-mini-evals-v2-focused":
        fail("unexpected focused mini-eval schema")
    if mini_evals.get("skill_name") != "deslop":
        fail("focused mini suite must target deslop")
    if mini_evals.get("corpus_revision") != CORPUS_REVISION:
        fail("focused mini suite does not identify the rc5 revision")
    mini_cases = mini_evals.get("evals")
    mini_by_id = {mini["id"]: mini for mini in adjudication["mini_repositories"]}
    if not isinstance(mini_cases, list) or {case.get("id") for case in mini_cases} != set(mini_by_id):
        fail("focused mini-eval ids do not match adjudication")
    for case in mini_cases:
        case_id = case["id"]
        if case.get("force_skill_invocation") is not True or case.get("assertions") != []:
            fail(f"{case_id}: mini eval must use explicit hidden grading")
        if "$deslop" in case.get("prompt", "") or "apply" not in case.get("prompt", "").lower():
            fail(f"{case_id}: mini prompt must authorize apply without leaking invocation syntax")
        files = case.get("files")
        repo = CORPUS / mini_by_id[case_id]["path"]
        expected_files = {
            path.relative_to(CORPUS).as_posix()
            for path in repo.iterdir()
            if path.is_file()
        }
        if not isinstance(files, list) or set(files) != expected_files:
            fail(f"{case_id}: mini eval must copy the complete miniature repository")
        for file_name in files:
            path = PurePosixPath(file_name)
            if path.is_absolute() or ".." in path.parts or not (CORPUS / file_name).is_file():
                fail(f"{case_id}: unsafe or missing mini fixture {file_name}")


def validate_cases(grader, adjudication: dict) -> None:
    insufficient_categories = set()
    for case in adjudication["cases"]:
        case_id = case["id"]
        fixture = CORPUS / "files" / case_id
        run_tests(grader, fixture, f"{case_id} before")
        try:
            grader.case_contract(case_id, fixture)
        except Exception as error:
            fail(f"{case_id}: before-state behavior gate failed: {error}")
        budget_passed, budget_evidence = grader.negative_change_budget(
            fixture,
            fixture,
            case["category"],
        )
        if not budget_passed:
            fail(f"{case_id}: unchanged fixture exceeds negative-change budget: {budget_evidence}")
        if case["expected"] == "simplify":
            try:
                grader.reduction_target(case_id, fixture)
            except Exception:
                pass
            else:
                fail(f"{case_id}: simplify before-state already satisfies reduction target")

        state = "golden_after" if case["expected"] == "simplify" else "destructive_mutant"
        with tempfile.TemporaryDirectory() as directory:
            calibrated = materialize(case_id, state, Path(directory))
            if case["expected"] == "simplify":
                run_tests(grader, calibrated, f"{case_id} golden_after")
                try:
                    grader.case_contract(case_id, calibrated)
                except Exception as error:
                    fail(f"{case_id}: golden_after hidden gate failed: {error}")
                try:
                    grader.reduction_target(case_id, calibrated)
                except Exception as error:
                    fail(f"{case_id}: golden_after reduction target failed: {error}")
                budget_passed, budget_evidence = grader.negative_change_budget(
                    fixture,
                    calibrated,
                    case["category"],
                )
                if not budget_passed:
                    fail(f"{case_id}: golden_after exceeds negative-change budget: {budget_evidence}")
            else:
                try:
                    grader.case_contract(case_id, calibrated)
                except Exception:
                    pass
                else:
                    fail(f"{case_id}: destructive_mutant still passes hidden gate")

        alternate = CORPUS / "calibration" / case_id / "alternate_valid"
        if alternate.is_dir():
            with tempfile.TemporaryDirectory() as directory:
                alternate_workspace = materialize(case_id, "alternate_valid", Path(directory))
                try:
                    grader.case_contract(case_id, alternate_workspace)
                except Exception as error:
                    fail(f"{case_id}: alternate_valid behavior gate failed: {error}")
                if case["expected"] == "simplify":
                    try:
                        grader.reduction_target(case_id, alternate_workspace)
                    except Exception as error:
                        fail(f"{case_id}: alternate_valid reduction target failed: {error}")
                run_tests(grader, alternate_workspace, f"{case_id} alternate_valid")
                budget_passed, budget_evidence = grader.negative_change_budget(
                    fixture,
                    alternate_workspace,
                    case["category"],
                )
                if not budget_passed:
                    fail(f"{case_id}: alternate_valid exceeds negative-change budget: {budget_evidence}")

        insufficient = CORPUS / "calibration" / case_id / "insufficient_cleanup"
        if insufficient.is_dir():
            if case["expected"] != "simplify":
                fail(f"{case_id}: preserve case cannot declare insufficient_cleanup")
            with tempfile.TemporaryDirectory() as directory:
                insufficient_workspace = materialize(case_id, "insufficient_cleanup", Path(directory))
                run_tests(grader, insufficient_workspace, f"{case_id} insufficient_cleanup")
                try:
                    grader.case_contract(case_id, insufficient_workspace)
                except Exception as error:
                    fail(f"{case_id}: insufficient_cleanup behavior gate failed: {error}")
                budget_passed, budget_evidence = grader.negative_change_budget(
                    fixture,
                    insufficient_workspace,
                    case["category"],
                )
                if not budget_passed:
                    fail(
                        f"{case_id}: insufficient_cleanup must isolate the reduction threshold: "
                        f"{budget_evidence}"
                    )
                before = grader.source_metrics(fixture)
                after = grader.source_metrics(insufficient_workspace)
                surface_keys = {
                    "test_bloat": ("test_count", "test_loc"),
                    "verification_theater": (
                        "checksum_mentions",
                        "verification_mentions",
                    ),
                    "defensive_fallback_bloat": (
                        "fallback_mentions",
                        "try_blocks",
                        "except_handlers",
                    ),
                }[case["category"]]
                if not any(after[key] < before[key] for key in surface_keys):
                    fail(f"{case_id}: insufficient_cleanup did not remove any target surface")
                try:
                    grader.reduction_target(case_id, insufficient_workspace)
                except Exception:
                    pass
                else:
                    fail(f"{case_id}: insufficient_cleanup incorrectly satisfies reduction target")
                insufficient_categories.add(case["category"])

    if insufficient_categories != set(adjudication["scope"]):
        fail(
            "insufficient_cleanup calibration must cover every focused category: "
            f"{sorted(insufficient_categories)}"
        )


def validate_mini_repositories(grader, adjudication: dict) -> None:
    for mini in adjudication["mini_repositories"]:
        repo = CORPUS / mini["path"]
        if not repo.is_dir():
            fail(f"missing mini repository: {mini['id']}")
        tests = grader.run_tests(repo)
        if not tests["passed"]:
            fail(f"{mini['id']}: baseline mini-repo tests failed: {tests}")
        try:
            grader.mini_behavior(repo, mini["category"])
        except Exception as error:
            fail(f"{mini['id']}: hidden externally meaningful behavior gate failed: {error}")
        comparison = grader.compare_mini_repositories(mini["category"], repo, repo)
        if not comparison["behavior_gate"]["passed"] or not comparison["eligible_for_reduction_scoring"]:
            fail(f"{mini['id']}: comparison refused to evaluate after-state metrics")
        for key in (
            "production_loc",
            "test_loc",
            "test_count",
            "fixture_invocations",
            "try_blocks",
            "checksum_mentions",
            "local_verifier_functions",
            "hash_operations",
            "fallback_nodes",
            "catch_fallback_handlers",
            "syntax_errors",
        ):
            if key not in comparison["metric_delta_after_minus_before"]:
                fail(f"{mini['id']}: comparison omitted metric {key}")
        if comparison["reduction_target"]["passed"]:
            fail(f"{mini['id']}: untouched mini repository satisfies reduction target")
        if not comparison["negative_change_budget"]["passed"]:
            fail(f"{mini['id']}: untouched mini repository exceeds negative-change budget")
        metrics = grader.source_metrics(repo)
        if metrics["production_loc"] <= 0 or metrics["test_loc"] <= 0 or metrics["test_count"] <= 0:
            fail(f"{mini['id']}: missing baseline reduction metrics")
        if mini["category"] == "test_bloat" and metrics["test_count"] < 5:
            fail("test-bloat mini repository must contain accumulated test volume")
        if mini["category"] == "verification_theater" and metrics["checksum_mentions"] < 3:
            fail("verification-bloat mini repository must contain a checksum cluster")
        if mini["category"] == "defensive_fallback_bloat" and metrics["fallback_mentions"] < 3:
            fail("fallback-bloat mini repository must contain fallback/compatibility machinery")

        golden = MINI_CALIBRATION / mini["id"] / "golden_after"
        if not golden.is_dir():
            fail(f"{mini['id']}: missing known-good golden_after mini repository")
        golden_tests = grader.run_tests(golden)
        if not golden_tests["passed"]:
            fail(f"{mini['id']}: golden_after tests failed: {golden_tests}")
        try:
            grader.mini_behavior(golden, mini["category"])
        except Exception as error:
            fail(f"{mini['id']}: golden_after behavior gate failed: {error}")
        comparison = grader.compare_mini_repositories(mini["category"], repo, golden)
        if not comparison["eligible_for_reduction_scoring"]:
            fail(f"{mini['id']}: golden_after is not reduction-eligible")
        if not comparison["reduction_target"]["passed"]:
            fail(
                f"{mini['id']}: golden_after misses meaningful reduction target: "
                f"{comparison['reduction_target']['evidence']}"
            )
        if not comparison["negative_change_budget"]["passed"]:
            fail(
                f"{mini['id']}: golden_after exceeds negative-change budget: "
                f"{comparison['negative_change_budget']['evidence']}"
            )
        delta = comparison["metric_delta_after_minus_before"]
        if mini["category"] == "test_bloat":
            if not (
                delta["test_loc"] < 0
                and delta["test_count"] < 0
                and delta["fixture_invocations"] < 0
            ):
                fail(f"{mini['id']}: golden_after did not reduce test surface: {delta}")
        elif mini["category"] == "verification_theater":
            if not (delta["checksum_mentions"] < 0 or delta["verification_mentions"] < 0):
                fail(f"{mini['id']}: golden_after did not reduce verification machinery: {delta}")
        elif mini["category"] == "defensive_fallback_bloat":
            if not (delta["fallback_nodes"] < 0 or delta["try_blocks"] < 0 or delta["fallback_mentions"] < 0):
                fail(f"{mini['id']}: golden_after did not reduce fallback machinery: {delta}")

    test_repo = CORPUS / "mini-repos" / "test-bloat"
    with tempfile.TemporaryDirectory() as directory:
        broken_after = Path(directory) / "broken-after"
        shutil.copytree(test_repo, broken_after)
        (broken_after / "test_reporting.py").write_text("import unittest\n\nclass Broken(unittest.TestCase):\n    def test_broken(self):\n        self.fail('broken')\n")
        try:
            grader.compare_mini_repositories("test_bloat", test_repo, broken_after)
        except Exception:
            pass
        else:
            fail("mini-repo comparison returned reduction eligibility after remaining tests failed")


def validate_negative_change_gate(grader) -> None:
    def reject_mutation(
        case_id: str,
        label: str,
        relative_path: str,
        content: str,
        expected_violation: str,
        *,
        append: bool = True,
        behavior_should_pass: bool = True,
    ) -> None:
        fixture = CORPUS / "files" / case_id
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / label
            shutil.copytree(fixture, workspace)
            path = workspace / relative_path
            if append:
                path.write_text(path.read_text() + content)
            else:
                path.write_text(content)
            if behavior_should_pass:
                run_tests(grader, workspace, f"negative gate {label}")
                try:
                    grader.case_contract(case_id, workspace)
                except Exception as error:
                    fail(f"negative gate {label}: behavior changed unexpectedly: {error}")
            passed, evidence = grader.negative_change_budget(
                fixture,
                workspace,
                grader.case_category(case_id),
            )
            if passed or expected_violation not in evidence:
                fail(f"negative gate accepted {label}: {evidence}")

    reject_mutation(
        "t01b",
        "new-python-file",
        "extra.py",
        "def helper_wrapper(value):\n    return value\n",
        "new Python files",
        append=False,
    )
    reject_mutation(
        "t01b",
        "new-test",
        "test_app.py",
        "\n\nclass AddedTests(unittest.TestCase):\n    def test_added(self):\n        self.assertTrue(True)\n",
        "new tests",
    )
    reject_mutation(
        "t01b",
        "loc-growth",
        "app.py",
        "\nEXTRA_1 = 1\nEXTRA_2 = 2\nEXTRA_3 = 3\nEXTRA_4 = 4\nEXTRA_5 = 5\n",
        "Python LOC growth",
    )
    reject_mutation(
        "t01b",
        "new-wrapper",
        "app.py",
        "\n\ndef result_wrapper(value):\n    return value\n",
        "new wrappers or abstractions",
    )
    reject_mutation(
        "v01b",
        "new-verification",
        "app.py",
        "\n\ndef validate_local(value):\n    return value\n",
        "new category-target machinery",
    )
    reject_mutation(
        "t01b",
        "new-dependency",
        "app.py",
        "\nimport decimal\n",
        "new dependencies",
    )
    reject_mutation(
        "t01b",
        "syntax-error",
        "app.py",
        "\ndef broken(:\n",
        "Python syntax errors",
        behavior_should_pass=False,
    )


def main() -> None:
    evals = json.loads(EVALS.read_text())
    mini_evals = json.loads(MINI_EVALS.read_text())
    adjudication = json.loads(ADJUDICATION.read_text())
    validate_manifest(evals, mini_evals, adjudication)
    grader = load_grader()
    validate_cases(grader, adjudication)
    validate_negative_change_gate(grader)
    validate_mini_repositories(grader, adjudication)
    print(
        "Validated dev-v2-focused-rc5: 16 paired micro cases, 3 insufficient-cleanup "
        "calibrations, negative-change gates, and 3 model-runnable mini repositories."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"focused validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
