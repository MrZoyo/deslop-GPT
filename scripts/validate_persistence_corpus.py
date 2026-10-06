#!/usr/bin/env python3
"""Calibrate stored-input/lifecycle gates without modifying corpus fixtures."""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "evals/dev-v4-persistence"
spec = importlib.util.spec_from_file_location("persistence_grader", CORPUS / "grade_persistence.py")
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)
manifest = json.loads((CORPUS / "evals.json").read_text())
assert {case["id"] for case in manifest["evals"]} == grader.CASES
states = 0
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for case in manifest["evals"]:
        case_id = case["id"]
        expected_files = {f"files/{case_id}/{name}" for name in ("app.py", "test_app.py", "CONTRACT.txt")}
        assert set(case["files"]) == expected_files
        for name in case["files"]:
            assert (CORPUS / name).is_file()
        original = root / f"{case_id}-original"
        shutil.copytree(CORPUS / "files" / case_id, original)
        assert grader.remaining_tests(original)["passed"], case_id
        original_result = grader.grade(case_id, original)
        assert not original_result["passed"], "unmodified slop must not pass cleanup"
        for overlay in sorted((CORPUS / "calibration" / case_id).iterdir()):
            workspace = root / f"{case_id}-{overlay.name}"
            shutil.copytree(CORPUS / "files" / case_id, workspace)
            for source in overlay.iterdir():
                shutil.copy2(source, workspace / source.name)
            result = grader.grade(case_id, workspace)
            expected = overlay.name in {"golden_after", "alternate_valid"}
            assert result["passed"] == expected, (case_id, overlay.name, result)
            assert grader.remaining_tests(workspace)["passed"], (case_id, overlay.name)
            if "mutant" in overlay.name:
                assert not result["assertions"][0]["passed"], "mutant must violate a real contract"
            if overlay.name == "insufficient_cleanup":
                assert result["assertions"][0]["passed"], "insufficient cleanup must preserve the contract"
                assert not result["assertions"][1]["passed"]
            states += 1
assert states == 9
print("Validated dev-v4-persistence-draft1: two lifecycle counterexamples, four valid states, three green-suite destructive mutants, and two insufficient cleanups.")
