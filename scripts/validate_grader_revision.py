#!/usr/bin/env python3
"""Validate equivalent rejection assertions and a real schema-regression mutant."""
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
PATH = REPO / "evals/grader-revisions/edge-coverage-v1/grade.py"
spec = importlib.util.spec_from_file_location("edge_revision", PATH)
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)
corpus = grader.BASE_PATH.parent

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for state in ("golden_after", "alternate_valid", "alternate_valid_reader_group"):
        workspace = root / state
        shutil.copytree(corpus / "files/s01a", workspace)
        for source in (corpus / "calibration/s01a" / state).rglob("*"):
            if source.is_file():
                shutil.copy2(source, workspace / source.name)
        assert grader.base.run_tests(workspace)["passed"], state
        assert grader.base.case_target("s01a", workspace), state
        tests = workspace / "test_app.py"
        content = tests.read_text()
        assert ".assertRaises(ValueError)" in content
        tests.write_text(content.replace(".assertRaises(ValueError)", '.assertRaisesRegex(ValueError, ".*")'))
        assert grader.base.run_tests(workspace)["passed"], state
        assert grader.base.case_target("s01a", workspace), state
        shutil.copy2(corpus / "files/s01a/app.py", workspace / "app.py")
        assert not grader.base.run_tests(workspace)["passed"], "regressed montage schema must fail the regex suite"
    missing = root / "missing-coverage"
    shutil.copytree(corpus / "files/s01a", missing)
    shutil.copy2(corpus / "calibration/s01a/golden_after/app.py", missing / "app.py")
    assert grader.base.run_tests(missing)["passed"]
    assert not grader.raised_call_covered(missing, "montage_frames")

print("Validated edge-coverage-v1: direct and reader-loop regex assertions detect schema regression; missing coverage stays rejected; draft4 budgets unchanged.")
