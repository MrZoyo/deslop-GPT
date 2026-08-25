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
ADJUDICATION = CORPUS / "adjudication.json"
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


def validate_manifest(evals: dict, adjudication: dict) -> None:
    if evals.get("schema") != "deslop-evals-v2-focused":
        fail("unexpected focused eval schema")
    if evals.get("skill_name") != "deslop":
        fail("focused suite must target deslop")
    if evals.get("corpus_version") != "dev-v2-focused":
        fail("unexpected focused corpus version")
    cases = evals.get("evals")
    if not isinstance(cases, list) or {case.get("id") for case in cases} != CASE_IDS:
        fail("focused eval ids do not match the 16-case taxonomy")
    adjudication_cases = adjudication.get("cases")
    if not isinstance(adjudication_cases, list) or {case.get("id") for case in adjudication_cases} != CASE_IDS:
        fail("focused adjudication ids do not match eval ids")
    if adjudication.get("scope") != {"test_bloat": 4, "verification_theater": 2, "defensive_fallback_bloat": 2}:
        fail("focused category mix must remain 4/2/2 deletion cases")

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


def validate_cases(grader, adjudication: dict) -> None:
    for case in adjudication["cases"]:
        case_id = case["id"]
        fixture = CORPUS / "files" / case_id
        run_tests(grader, fixture, f"{case_id} before")
        try:
            grader.case_contract(case_id, fixture)
        except Exception:
            if case["expected"] == "preserve":
                raise
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
        for key in ("production_loc", "test_loc", "test_count", "try_blocks", "checksum_mentions", "fallback_nodes"):
            if key not in comparison["metric_delta_after_minus_before"]:
                fail(f"{mini['id']}: comparison omitted metric {key}")
        metrics = grader.source_metrics(repo)
        if metrics["production_loc"] <= 0 or metrics["test_loc"] <= 0 or metrics["test_count"] <= 0:
            fail(f"{mini['id']}: missing baseline reduction metrics")
        if mini["category"] == "test_bloat" and metrics["test_count"] < 5:
            fail("test-bloat mini repository must contain accumulated test volume")
        if mini["category"] == "verification_theater" and metrics["checksum_mentions"] < 3:
            fail("verification-bloat mini repository must contain a checksum cluster")
        if mini["category"] == "defensive_fallback_bloat" and metrics["fallback_mentions"] < 3:
            fail("fallback-bloat mini repository must contain fallback/compatibility machinery")

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


def main() -> None:
    evals = json.loads(EVALS.read_text())
    adjudication = json.loads(ADJUDICATION.read_text())
    validate_manifest(evals, adjudication)
    grader = load_grader()
    validate_cases(grader, adjudication)
    validate_mini_repositories(grader, adjudication)
    print("Validated dev-v2-focused: 16 paired cases (8 simplify/8 preserve), 4/2/2 category mix, and 3 mini-repository behavior gates.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"focused validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
