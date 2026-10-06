#!/usr/bin/env python3
"""Held-back deterministic checks. CLI: grade_transfer.py CASE_ID WORKSPACE."""
import ast
import contextlib
import functools
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

CASES = {
    "csv_keep_v1": ("csv", True),
    "csv_retire_v1": ("csv", False),
    "sqlite_keep_v1": ("sqlite", True),
    "sqlite_retire_v1": ("sqlite", False),
}

# These literals and SQL never pass through the module's writer.
OLD_CSV = 'stock-v1,00012,"hinge, brass"'
OLD_SQL = """
CREATE TABLE stock (name TEXT PRIMARY KEY, units TEXT);
INSERT INTO stock VALUES ('hinge, brass', '00012');
INSERT INTO stock VALUES ('齿轮', '0');
PRAGMA user_version = 1;
"""
OLD_EXPECTED = [{"item": "hinge, brass", "quantity": 12},
                {"item": "齿轮", "quantity": 0}]


def require(condition, message="contract assertion failed"):
    if not condition:
        raise AssertionError(message)


def expect_rejected(operation, retired=False):
    try:
        operation()
    except ValueError as exc:
        if retired:
            require("retired" in str(exc).lower(), "retirement must be visible")
        return
    raise AssertionError("expected ValueError")


def sql_file(path, script):
    with sqlite3.connect(path) as db:
        db.executescript(script)


def sql_snapshot(path):
    with sqlite3.connect(path) as db:
        return (db.execute("PRAGMA user_version").fetchone()[0],
                tuple(db.iterdump()))


def check_behavior(app, kind, supported):
    checks = []

    def check(name, operation):
        try:
            operation()
            checks.append({"name": name, "passed": True})
        except Exception as exc:
            checks.append({"name": name, "passed": False,
                           "detail": type(exc).__name__ + ": " + str(exc)})

    if kind == "csv":
        def current():
            expected = 'stock-v2,"hinge, ""brass""",12'
            require(app.encode_item('hinge, "brass"', 12) == expected)
            require(app.decode_item(expected) == {"item": 'hinge, "brass"', "quantity": 12})
            require(app.decode_item("stock-v2,  齿轮  ,000") == {"item": "  齿轮  ", "quantity": 0})

        def legacy():
            if supported:
                require(app.decode_item(OLD_CSV) == OLD_EXPECTED[0])
                require(app.decode_item("stock-v1,0,  齿轮  ") == {"item": "  齿轮  ", "quantity": 0})
            else:
                expect_rejected(lambda: app.decode_item(OLD_CSV), retired=True)
                expect_rejected(lambda: app.decode_item("stock-v1,0,  齿轮  "), retired=True)

        def writer_rejection():
            for args in [("x", True), ("x", -2), ("x", "2"), (" ", 2), ("a\nb", 1)]:
                expect_rejected(lambda args=args: app.encode_item(*args))

        def corruption():
            for value in ["stock-v2,x,-2", "stock-v2,x,+2", "stock-v2,x,1.5",
                          "stock-v2,x,２", "stock-v2, ,2", "stock-v2,x,2,extra",
                          "stock-v7,x,2", 'stock-v2,"unclosed,2',
                          "stock-v2,x,2\nstock-v2,y,3", "", None]:
                expect_rejected(lambda value=value: app.decode_item(value))
            if supported:
                for value in ["stock-v1,-2,x", "stock-v1,+2,x", "stock-v1,nope,x",
                              "stock-v1,2, "]:
                    expect_rejected(lambda value=value: app.decode_item(value))

        check("current_operations_and_values", current)
        check("fixed_legacy_lifecycle", legacy)
        check("writer_input_rejection", writer_rejection)
        check("external_record_rejection", corruption)
    else:
        with tempfile.TemporaryDirectory(prefix="transfer-sql-") as temp:
            root = Path(temp)

            def current():
                path = root / "current.sqlite"
                require(app.write_inventory(path, [("齿轮", 0), ('hinge, "brass"', 12)]) == 2)
                expected = [{"item": 'hinge, "brass"', "quantity": 12},
                            {"item": "齿轮", "quantity": 0}]
                before = sql_snapshot(path)
                require(app.read_inventory(path) == expected)
                require(sql_snapshot(path) == before, "read changed stored database")
                require(app.write_inventory(path, [("  spacer  ", 3)]) == 1)
                require(app.read_inventory(path) == [{"item": "  spacer  ", "quantity": 3}])
                require(app.write_inventory(path, []) == 0)
                require(app.read_inventory(path) == [])

            def legacy():
                path = root / "fixed-old.sqlite"
                sql_file(path, OLD_SQL)
                before = sql_snapshot(path)
                if supported:
                    require(app.read_inventory(path) == OLD_EXPECTED)
                else:
                    expect_rejected(lambda: app.read_inventory(path), retired=True)
                require(sql_snapshot(path) == before, "legacy read changed database")
                expect_rejected(lambda: app.write_inventory(path, [("new", 1)]))
                require(sql_snapshot(path) == before, "write changed old database")

            def writer_rejection():
                path = root / "writer.sqlite"
                app.write_inventory(path, [("kept", 8)])
                before = sql_snapshot(path)
                for rows in [[("x", True)], [("x", -2)], [("x", "2")],
                             [(" ", 2)], [("x", 1), ("x", 2)]]:
                    expect_rejected(lambda rows=rows: app.write_inventory(path, rows))
                    require(sql_snapshot(path) == before, "invalid input changed database")
                unknown = root / "unknown-write.sqlite"
                sql_file(unknown, "CREATE TABLE note (value TEXT); INSERT INTO note VALUES ('keep'); PRAGMA user_version=9;")
                snapshot = sql_snapshot(unknown)
                expect_rejected(lambda: app.write_inventory(unknown, [("new", 1)]))
                require(sql_snapshot(unknown) == snapshot, "write changed unknown database")

            def corruption():
                scripts = [
                    "CREATE TABLE inventory_items (item TEXT, quantity); INSERT INTO inventory_items VALUES ('x', -2); PRAGMA user_version=2;",
                    "CREATE TABLE inventory_items (item TEXT, quantity); INSERT INTO inventory_items VALUES ('x', 'bad'); PRAGMA user_version=2;",
                    "CREATE TABLE inventory_items (item TEXT, quantity); INSERT INTO inventory_items VALUES ('x', 1.5); PRAGMA user_version=2;",
                    "CREATE TABLE inventory_items (item TEXT, quantity); INSERT INTO inventory_items VALUES (' ', 1); PRAGMA user_version=2;",
                    "CREATE TABLE inventory_items (item TEXT, quantity); INSERT INTO inventory_items VALUES ('x', 1), ('x', 2); PRAGMA user_version=2;",
                    "PRAGMA user_version=2;", "PRAGMA user_version=9;",
                ]
                if supported:
                    scripts += ["CREATE TABLE stock (name TEXT, units TEXT); INSERT INTO stock VALUES ('x', '" + units + "'); PRAGMA user_version=1;"
                                for units in ("-2", "+2", "1.5", "bad", "２")]
                    scripts += ["CREATE TABLE stock (name TEXT, units TEXT); INSERT INTO stock VALUES (' ', '2'); PRAGMA user_version=1;"]
                for index, script in enumerate(scripts):
                    path = root / ("corrupt-" + str(index) + ".sqlite")
                    sql_file(path, script)
                    before = sql_snapshot(path)
                    expect_rejected(lambda path=path: app.read_inventory(path))
                    require(sql_snapshot(path) == before, "corrupt read changed database")
                path = root / "broken.sqlite"
                path.write_bytes(b"this is not a SQLite database")
                expect_rejected(lambda: app.read_inventory(path))

            check("current_operations_and_values", current)
            check("fixed_legacy_lifecycle_and_read_only", legacy)
            check("writer_input_rejection_and_no_replacement", writer_rejection)
            check("external_database_rejection", corruption)
    return {"passed": all(entry["passed"] for entry in checks), "checks": checks}


def retained_suite(app, workspace, kind):
    coverage = {"writer_success": 0, "current_reader_success": 0,
                "writer_rejection": 0, "reader_rejection": 0,
                "legacy_reader_success": 0}
    writer_name, reader_name = (("encode_item", "decode_item") if kind == "csv"
                                else ("write_inventory", "read_inventory"))
    originals = {name: getattr(app, name) for name in (writer_name, reader_name)}

    def wrap(name):
        original = originals[name]

        @functools.wraps(original)
        def observed(*args, **kwargs):
            old = False
            if name == reader_name:
                if kind == "csv":
                    old = bool(args and isinstance(args[0], str) and args[0].startswith("stock-v1,"))
                else:
                    try:
                        with sqlite3.connect(args[0]) as db:
                            old = db.execute("PRAGMA user_version").fetchone()[0] == 1
                    except Exception:
                        pass
            try:
                result = original(*args, **kwargs)
            except ValueError:
                coverage["writer_rejection" if name == writer_name else "reader_rejection"] += 1
                raise
            coverage["writer_success" if name == writer_name else
                     "legacy_reader_success" if old else "current_reader_success"] += 1
            return result
        return observed

    try:
        for name in originals:
            setattr(app, name, wrap(name))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            suite = unittest.defaultTestLoader.discover(str(workspace), pattern="test*.py", top_level_dir=str(workspace))
            result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
        useful = all(coverage[name] > 0 for name in ("writer_success", "current_reader_success", "writer_rejection", "reader_rejection"))
        return {"passed": result.wasSuccessful() and result.testsRun > 0 and useful,
                "suite_passed": result.wasSuccessful(), "tests_run": result.testsRun,
                "meaningful_current_coverage": useful, "coverage": coverage,
                "failure_count": len(result.failures), "error_count": len(result.errors),
                "output": stream.getvalue()[-2500:] if not result.wasSuccessful() else ""}
    finally:
        for name, original in originals.items():
            setattr(app, name, original)


def removal_checks(app, workspace, kind, supported, suite):
    fingerprints = []
    production_files = [path for path in workspace.rglob("*.py") if not path.name.startswith("test")]
    for path in production_files:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                fingerprints += [str(path.relative_to(workspace)) + ":" + alias.name for alias in node.names if alias.name.split(".")[0] in {"hashlib", "hmac", "zlib"}]
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in {"hashlib", "hmac", "zlib"}:
                fingerprints.append(str(path.relative_to(workspace)) + ":" + node.module)
            elif isinstance(node, ast.Attribute) and node.attr in {"hexdigest", "digest", "crc32", "adler32"}:
                fingerprints.append(str(path.relative_to(workspace)) + ":" + node.attr)
    retained_decoder = []
    if not supported:
        public = {"encode_item", "decode_item", "write_inventory", "read_inventory"}
        local_functions = {}
        for module in list(sys.modules.values()):
            module_path = getattr(module, "__file__", None)
            if not module_path:
                continue
            try:
                local = Path(module_path).resolve().is_relative_to(workspace)
            except (TypeError, ValueError, OSError):
                continue
            if not local or Path(module_path).name.startswith("test"):
                continue
            for name, function in vars(module).items():
                if name not in public and inspect.isfunction(function):
                    local_functions[id(function)] = (module.__name__ + "." + name, function)
        for name, function in local_functions.values():
            try:
                parameters = list(inspect.signature(function).parameters.values())
            except (TypeError, ValueError):
                continue
            if len(parameters) != 1 or parameters[0].kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                continue
            try:
                if kind == "csv":
                    output = function(["stock-v1", "00012", "hinge, brass"])
                    match = output == OLD_EXPECTED[0]
                else:
                    with sqlite3.connect(":memory:") as db:
                        db.executescript(OLD_SQL)
                        output = function(db)
                    match = output == OLD_EXPECTED
                if match:
                    retained_decoder.append(name)
            except Exception:
                pass
    checks = {"self_only_fingerprints_removed": not fingerprints,
              "retired_semantic_decoder_removed": not retained_decoder,
              "retired_success_tests_removed": supported or suite["coverage"]["legacy_reader_success"] == 0}
    return {"passed": all(checks.values()), "checks": checks,
            "fingerprint_evidence": sorted(set(fingerprints)),
            "retained_decoder_evidence": retained_decoder}


def worker(case_id, workspace):
    kind, supported = CASES[case_id]
    sys.path.insert(0, str(workspace))
    spec = importlib.util.spec_from_file_location("app", workspace / "app.py")
    app = importlib.util.module_from_spec(spec)
    sys.modules["app"] = app
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(app)
    behavior = check_behavior(app, kind, supported)
    suite = retained_suite(app, workspace, kind)
    removal = removal_checks(app, workspace, kind, supported, suite)
    production = [(path, path.read_text()) for path in sorted(workspace.rglob("*.py")) if not path.name.startswith("test")]
    test_files = sorted(workspace.rglob("test*.py"))
    metrics = {"production_file_count": len(production),
               "production_lines": sum(len(source.splitlines()) for _, source in production),
               "production_bytes": sum(len(source.encode()) for _, source in production),
               "production_function_count": sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for _, source in production for node in ast.walk(ast.parse(source))),
               "test_file_count": len(test_files),
               "test_source_bytes": sum(path.stat().st_size for path in test_files),
               "remaining_tests_run": suite["tests_run"]}
    return {"case_id": case_id, "passed": behavior["passed"] and suite["passed"] and removal["passed"],
            "behavior": behavior, "remaining_tests": suite, "removal": removal, "metrics": metrics}


def failed_result(case_id, error):
    return {"case_id": case_id, "passed": False, "error": error,
            "behavior": {"passed": False, "checks": [], "unverified": True},
            "remaining_tests": {"passed": False, "tests_run": 0, "unverified": True},
            "removal": {"passed": False, "checks": {}, "unverified": True},
            "metrics": {"unverified": True}}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        case_id, workspace_text = sys.argv[2:]
        try:
            result = worker(case_id, Path(workspace_text).resolve())
        except Exception as exc:
            result = failed_result(case_id, type(exc).__name__ + ": " + str(exc))
        print(json.dumps(result, sort_keys=True))
        return 0
    if len(sys.argv) != 3 or sys.argv[1] not in CASES:
        print(json.dumps({"passed": False, "error": "usage: grade_transfer.py CASE_ID WORKSPACE"}))
        return 2
    case_id, workspace = sys.argv[1:]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", case_id, workspace],
                                 capture_output=True, text=True, timeout=15, env=env)
        if process.returncode:
            raise RuntimeError("worker failed: " + process.stderr[-1500:])
        result = json.loads(process.stdout)
    except Exception as exc:
        result = failed_result(case_id, type(exc).__name__ + ": " + str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
