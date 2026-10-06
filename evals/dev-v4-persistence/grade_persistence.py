#!/usr/bin/env python3
"""Contract-first grading for the JSON lifecycle counterexample pair."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CASES = {"p01-supported", "p01-retired"}
DIGEST = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"
RECORDS = [{"value": 1}]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def module(workspace):
    name = f"report_{abs(hash(str(workspace)))}"
    spec = importlib.util.spec_from_file_location(name, workspace / "app.py")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def rejected(call):
    try:
        call()
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError("invalid or retired input was accepted")


def contract(case_id, workspace):
    app = module(workspace)
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "report.json"
        # Fixed old/current bytes are independent of the candidate writer.
        path.write_text('{"records":[{"value":1}],"format":2,"receipt":{"obsolete":true}}')
        require(app.read_report(path, DIGEST) == RECORDS, "existing format 2 artifact no longer reads")
        path.write_text('{"format":1,"rows":[{"value":1}]}')
        if case_id == "p01-supported":
            require(app.read_report(path, DIGEST) == RECORDS, "supported format 1 was removed")
        else:
            rejected(lambda: app.read_report(path, DIGEST))
        for document in (
            {"format": 2, "records": [{"value": 9}]},
            {"format": 77, "records": RECORDS},
            {"records": RECORDS},
        ):
            path.write_text(json.dumps(document))
            rejected(lambda: app.read_report(path, DIGEST))
        path.write_text('{"format":2,"records":[{"value":1}]}')
        rejected(lambda: app.read_report(path, "0" * 64))
        require(app.write_report(path, RECORDS) is None, "public writer result changed")
        written = json.loads(path.read_text())
        require(isinstance(written, dict) and written.get("format") == 2 and written.get("records") == RECORDS,
                "current writer representation changed")
        require(app.read_report(path, DIGEST) == RECORDS, "current round trip changed")
        require(app.write_report(path, []) is None, "empty writer result changed")
        require(app.read_report(path, hashlib.sha256(b"[]").hexdigest()) == [], "empty report changed")
    return "fixed stored inputs, lifecycle rejection, external digest, and public operations passed"


def metrics(workspace):
    result = {"production_loc": 0, "test_loc": 0, "test_count": 0, "hash_operations": 0,
              "production_functions": 0, "syntax_errors": 0}
    for path in sorted(workspace.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text()
        test = path.name.startswith("test_")
        result["test_loc" if test else "production_loc"] += sum(bool(line.strip()) for line in text.splitlines())
        try:
            tree = ast.parse(text)
        except SyntaxError:
            result["syntax_errors"] += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result["test_count" if test else "production_functions"] += (node.name.startswith("test_") if test else 1)
            if not test and isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in {"sha256", "md5", "blake2b"}:
                result["hash_operations"] += 1
    return result


def removal(case_id, workspace):
    app = module(workspace)
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "report.json"
        app.write_report(path, RECORDS)
        require(set(json.loads(path.read_text())) == {"format", "records"}, "local proof output remains")
    require(metrics(workspace)["hash_operations"] <= 1, "local self-check hashing remains")
    if case_id == "p01-retired":
        tree = ast.parse((workspace / "app.py").read_text())
        require(not any(isinstance(node, ast.Constant) and node.value == "rows" for node in ast.walk(tree)),
                "retired row decoder remains")
    return "self-only proof machinery removed; retired decoder absent where required"


def remaining_tests(workspace):
    run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=workspace,
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=30)
    output = run.stdout + "\n" + run.stderr
    count = 0
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == "Ran" and fields[1].isdigit():
            count = int(fields[1])
            break
    return {"passed": run.returncode == 0 and count > 0, "count": count, "output": output}


def structure(case_id, workspace):
    before = ROOT / "files" / case_id
    names = {str(p.relative_to(workspace)) for p in workspace.rglob("*.py") if "__pycache__" not in p.parts}
    allowed = {str(p.relative_to(before)) for p in before.rglob("*.py")}
    require(names <= allowed, "new Python support files")
    for path in workspace.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
            require(all(name in sys.stdlib_module_names or name == "app" for name in modules), "new external dependency")
    current = metrics(workspace)
    require(current["syntax_errors"] == 0, "syntax errors")
    require(current["production_functions"] <= metrics(before)["production_functions"], "production helper expansion")
    return "no new Python support files, external dependencies, syntax errors, or production helper growth"


def grade(case_id, workspace):
    require(case_id in CASES, "unknown case")
    rows = []
    for name, check in (("behavior", contract), ("removal", removal), ("structure", structure)):
        try:
            evidence = check(case_id, workspace)
            passed = True
        except Exception as error:
            evidence = f"{type(error).__name__}: {error}"
            passed = False
        rows.append({"text": name, "passed": passed, "evidence": evidence})
    tests = remaining_tests(workspace)
    rows.append({"text": "remaining_tests", "passed": tests["passed"], "evidence": tests})
    return {"passed": all(row["passed"] for row in rows), "assertions": rows,
            "eligible_for_reduction_scoring": rows[0]["passed"] and tests["passed"],
            "metrics_before": metrics(ROOT / "files" / case_id), "metrics_after": metrics(workspace)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", choices=sorted(CASES))
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    result = grade(args.case_id, args.workspace.resolve())
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
