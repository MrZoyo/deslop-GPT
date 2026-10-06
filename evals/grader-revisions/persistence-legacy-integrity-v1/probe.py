#!/usr/bin/env python3
"""Post-run legacy-integrity probe; preserve the frozen JSON draft1 scores."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
CORPUS = Path(__file__).resolve().parents[2] / "dev-v4-persistence"
spec = importlib.util.spec_from_file_location("persistence_draft1", CORPUS / "grade_persistence.py")
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)


def probe(workspace):
    app = grader.module(workspace)
    checks = []
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "report.json"
        for name, document, digest, reject in (
            ("valid_legacy", '{"format":1,"rows":[{"value":1}]}', grader.DIGEST, False),
            ("corrupt_legacy", '{"format":1,"rows":[{"value":9}]}', grader.DIGEST, True),
            ("wrong_legacy_digest", '{"format":1,"rows":[{"value":1}]}', "0" * 64, True),
        ):
            path.write_text(document)
            try:
                if reject:
                    try:
                        app.read_report(path, digest)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("legacy corruption was accepted")
                else:
                    assert app.read_report(path, digest) == grader.RECORDS
                checks.append({"name": name, "passed": True})
            except Exception as error:
                checks.append({"name": name, "passed": False, "error": f"{type(error).__name__}: {error}"})
        try:
            assert app.write_report(path, grader.RECORDS) is None
            assert app.read_report(path, grader.DIGEST) == grader.RECORDS
            checks.append({"name": "current_operations", "passed": True})
        except Exception as error:
            checks.append({"name": "current_operations", "passed": False, "error": f"{type(error).__name__}: {error}"})
    return {"role": "post-run supplementary probe for p01-supported only; draft1 scores unchanged",
            "passed": all(check["passed"] for check in checks), "checks": checks}


def calibrate():
    rows = []
    with tempfile.TemporaryDirectory() as temporary:
        for state in ("original", "golden_after", "alternate_valid", "early_return_mutant", "reject_all_mutant"):
            workspace = Path(temporary) / state
            shutil.copytree(CORPUS / "files/p01-supported", workspace)
            overlay = "golden_after" if state.endswith("mutant") else state
            if overlay != "original":
                shutil.copytree(CORPUS / "calibration/p01-supported" / overlay, workspace, dirs_exist_ok=True)
            app = workspace / "app.py"
            if state == "early_return_mutant":
                source = app.read_text()
                assert source.count('records = document["rows"]') == 1
                app.write_text(source.replace('records = document["rows"]', 'return document["rows"]'))
                assert grader.grade("p01-supported", workspace)["passed"], "must reproduce draft1 blind spot"
            elif state == "reject_all_mutant":
                app.write_text(app.read_text() + '\ndef read_report(path, expected_sha256):\n    raise ValueError("reject all")\n')
            result = probe(workspace)
            expected = not state.endswith("mutant")
            assert result["passed"] == expected, (state, result)
            if state == "early_return_mutant":
                assert [row["passed"] for row in result["checks"]] == [True, False, False, True]
            if state == "reject_all_mutant":
                assert [row["passed"] for row in result["checks"]] == [False, True, True, False]
            rows.append({"state": state, "expected_pass": expected, "result": result})
    return {"passed": True, "calibration_states": len(rows), "states": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", type=Path)
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args()
    if args.calibrate:
        result = calibrate()
    elif args.workspace:
        result = probe(args.workspace.resolve())
    else:
        parser.error("provide a copied p01-supported workspace or --calibrate")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
