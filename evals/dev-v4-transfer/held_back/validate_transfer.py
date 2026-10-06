#!/usr/bin/env python3
"""Calibrate without editing fixture inputs; optionally write an external report."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
HIDDEN = ROOT / "held_back"


def input_hashes():
    inputs = list((ROOT / "cases").rglob("*")) + list((HIDDEN / "overlays").rglob("*"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(inputs) if path.is_file()}


def expected(case, state):
    if state in ("known_good", "alternate_valid"):
        return {"behavior": True, "remaining_tests": True, "removal": True}
    if state == "insufficient_cleanup":
        return {"behavior": True, "remaining_tests": True, "removal": False}
    if state == "mutant_dead_decoder":
        return {"behavior": True, "remaining_tests": True, "removal": False}
    if state == "baseline":
        return {"behavior": case["legacy_supported"], "remaining_tests": True, "removal": False}
    return {"behavior": False, "remaining_tests": True,
            "removal": state != "mutant_accept_retired"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    before = input_hashes()
    manifest = json.loads((HIDDEN / "manifest.json").read_text())
    rows = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for case in manifest["cases"]:
        case_id = case["case_id"]
        states = ["baseline", "known_good", "alternate_valid", "insufficient_cleanup"] + case["mutants"]
        for state in states:
            with tempfile.TemporaryDirectory(prefix="transfer-calibration-") as temp:
                workspace = Path(temp) / "fixture"
                shutil.copytree(ROOT / "cases" / case_id, workspace)
                if state != "baseline":
                    for name in ("app.py", "test_app.py"):
                        shutil.copy2(HIDDEN / "overlays" / case_id / state / name, workspace / name)
                try:
                    process = subprocess.run([sys.executable, str(HIDDEN / "grade_transfer.py"), case_id, str(workspace)],
                                             capture_output=True, text=True, timeout=20, env=env)
                    result = json.loads(process.stdout)
                except Exception as exc:
                    result = {"passed": False, "error": type(exc).__name__ + ": " + str(exc)}
                expectation = expected(case, state)
                matches = all(result.get(category, {}).get("passed") == value for category, value in expectation.items())
                matches = matches and result.get("passed") == all(expectation.values())
                rows.append({"case_id": case_id, "state": state,
                             "expected": expectation, "calibration_passed": matches,
                             "grade": result})
    after = input_hashes()
    output = {"passed": all(row["calibration_passed"] for row in rows) and before == after,
              "calibrations_run": len(rows),
              "calibrations_passed": sum(row["calibration_passed"] for row in rows),
              "inputs_unchanged": before == after,
              "input_sha256": before, "results": rows}
    if arguments.output:
        arguments.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: output[key] for key in ("passed", "calibrations_run", "calibrations_passed", "inputs_unchanged")}, sort_keys=True))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
