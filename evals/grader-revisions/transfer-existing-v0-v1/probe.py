#!/usr/bin/env python3
"""Supplementary existing-version-zero contract probe; no draft1 rescoring."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CASES = ("sqlite_keep_v1", "sqlite_retire_v1")


def load_app(workspace):
    spec = importlib.util.spec_from_file_location("existing_v0_candidate", workspace / "app.py")
    app = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = app
    spec.loader.exec_module(app)
    return app


def snapshot(path):
    with sqlite3.connect(path) as db:
        return {"version": db.execute("PRAGMA user_version").fetchone()[0],
                "rows": db.execute("SELECT * FROM inventory_items ORDER BY item").fetchall()}


def probe(app):
    checks = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        current = root / "current.sqlite"
        try:
            assert app.write_inventory(current, [("new", 3)]) == 1
            assert app.read_inventory(current) == [{"item": "new", "quantity": 3}]
            assert app.write_inventory(current, [("next", 4)]) == 1
            assert app.read_inventory(current) == [{"item": "next", "quantity": 4}]
            checks.append({"name": "new_and_current_operations", "passed": True})
        except Exception as error:
            checks.append({"name": "new_and_current_operations", "passed": False,
                           "error": f"{type(error).__name__}: {error}"})
        existing = root / "existing.sqlite"
        with sqlite3.connect(existing) as db:
            db.execute("CREATE TABLE inventory_items (item TEXT PRIMARY KEY, quantity INTEGER NOT NULL)")
            db.execute("INSERT INTO inventory_items VALUES ('keep', 7)")
            db.execute("PRAGMA user_version=0")
        before = snapshot(existing)
        error = None
        rejected_with_value_error = False
        try:
            returned = app.write_inventory(existing, [("replacement", 3)])
        except Exception as exc:
            error = type(exc).__name__
            rejected_with_value_error = isinstance(exc, ValueError)
            returned = None
        after = snapshot(existing)
        checks.append({"name": "existing_zero_rejected_without_replacement",
                       "passed": rejected_with_value_error and before == after,
                       "exception": error, "returned": returned, "before": before, "after": after})
    return {"role": "supplementary contract probe; draft1 scores remain unchanged",
            "passed": all(check["passed"] for check in checks), "checks": checks}


def calibrate():
    rows = []
    for case in CASES:
        source = ROOT.parents[1] / "dev-v4-transfer/cases" / case
        original = load_app(source)
        before = probe(original)
        assert not before["passed"] and before["checks"][0]["passed"]
        rows.append({"case": case, "state": "original", "expected_pass": False})
        write = original.write_inventory

        def guarded(path, items):
            if Path(path).exists():
                with sqlite3.connect(path) as db:
                    if db.execute("PRAGMA user_version").fetchone()[0] == 0:
                        raise ValueError("unsupported existing database version")
            return write(path, items)

        original.write_inventory = guarded
        assert probe(original)["passed"], case
        rows.append({"case": case, "state": "guarded_existing_zero", "expected_pass": True})

        def reject_all(path, items):
            raise ValueError("reject everything")

        original.write_inventory = reject_all
        rejected = probe(original)
        assert not rejected["passed"] and rejected["checks"][1]["passed"]
        rows.append({"case": case, "state": "reject_all_mutant", "expected_pass": False})
    return {"passed": True, "calibration_states": len(rows), "states": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", type=Path)
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args()
    if args.calibrate:
        result = calibrate()
    elif args.workspace:
        result = probe(load_app(args.workspace.resolve()))
    else:
        parser.error("provide a copied workspace or --calibrate")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
