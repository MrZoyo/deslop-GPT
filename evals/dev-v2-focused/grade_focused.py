#!/usr/bin/env python3
"""Small hidden-contract grader for the focused development corpus.

The script intentionally has no model or framework dependency.  It is used by
the corpus validator and can also be called as a post-grade hook for a focused
agent-skill-eval run.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(workspace: Path, name: str) -> str:
    return (workspace / name).read_text()


def module(workspace: Path, filename: str = "app.py"):
    path = workspace / filename
    module_name = f"focused_{path.stem}_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def test_functions(workspace: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(read(workspace, "test_app.py"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def run_tests(workspace: Path) -> dict[str, object]:
    started = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v"],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = "\n".join((result.stdout, result.stderr))
    count = 0
    for line in output.splitlines():
        if line.startswith("Ran "):
            count = int(line.split()[1])
            break
    return {
        "passed": result.returncode == 0 and count > 0,
        "count": count,
        "runtime_seconds": round(time.perf_counter() - started, 6),
    }


def case_contract(case_id: str, workspace: Path) -> str:
    app = module(workspace)
    tests = read(workspace, "test_app.py")
    functions = test_functions(workspace)

    if case_id == "t01a":
        require(len(functions) == 1, "redundant summary tests remain")
        require(app.summarize_records([{"name": "a"}]).names == ("a",), "summary behavior changed")
    elif case_id == "t01b":
        require(len(functions) >= 2, "distinct publication tests were removed")
        with tempfile.TemporaryDirectory() as directory:
            path = app.publish_records([{"name": "a"}], Path(directory) / "records.json")
            require('"name": "a"' in path.read_text(), "publication behavior changed")
            try:
                app.publish_records([], Path(directory) / "empty.json")
            except ValueError:
                pass
            else:
                raise AssertionError("empty publication was accepted")
    elif case_id == "t02a":
        require(len(functions) == 1, "private-helper test remains")
        require("_normalize_label" not in tests, "test still imports private helper")
        require(app.public_label("  Alpha   Beta ") == "alpha beta", "public label changed")
    elif case_id == "t02b":
        require(len(functions) >= 2, "current or legacy header coverage was removed")
        require(app.parse_header({"header": "v2"}) == "v2", "current header broke")
        require(app.parse_header({"legacy_header": "v1"}) == "v1", "legacy header broke")
    elif case_id == "t03a":
        require(len(functions) == 1, "successive duplicate normalization tests remain")
        require(app.normalize_identifier("  Device A  ") == "device-a", "identifier changed")
    elif case_id == "t03b":
        require(len(functions) >= 2, "distinct identifier edge tests were removed")
        with _raises(ValueError):
            app.normalize_identifier("")
        require(app.normalize_identifier(" Straße ") == "strasse", "unicode normalization broke")
    elif case_id == "t04a":
        require(len(functions) == 1, "wrapper-only tests remain")
        require("format_user" not in read(workspace, "app.py"), "pass-through wrapper remains")
        require(app.render_user("Ada") == "User: Ada", "renderer behavior changed")
    elif case_id == "t04b":
        require(len(functions) >= 1, "wire contract test was removed")
        require(app.export_wire_user("Ada") == b'USR/1 {"display": "User: Ada"}', "wire contract changed")
    elif case_id == "v01a":
        text = read(workspace, "app.py") + tests
        require("hashlib" not in text and "checksum" not in text, "self-generated checksum cluster remains")
        require(not hasattr(app, "validate_report"), "self-validator remains")
        require(app.build_report([{"name": "a"}]) == {"records": [{"name": "a"}]}, "report behavior changed")
    elif case_id == "v01b":
        expected = "26717ae4369d005dc210693d1d9256de56b5689078ed07922317ea56020a6486"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.bin"
            app.write_artifact(path, b"public-fixture")
            require(app.verify_artifact(path, expected) == b"public-fixture", "external digest failed")
            path.write_bytes(b"tampered")
            with _raises(ValueError):
                app.verify_artifact(path, expected)
    elif case_id == "v02a":
        text = read(workspace, "app.py") + tests
        require("receipt" not in text and "validate_receipt" not in text, "local receipt cluster remains")
        require(app.process(3) == 6, "process behavior changed")
    elif case_id == "v02b":
        manifest = {"size": 13, "sha256": "9d7ec3059a3be4a437e8028d9a498f2fd4adfa7183af52ecc712704ee1dc8260"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            app.write_package(path, b"package-bytes")
            require(app.load_package(path, manifest) == b"package-bytes", "manifest verification failed")
            path.write_bytes(b"corrupted")
            with _raises(ValueError):
                app.load_package(path, manifest)
    elif case_id == "f01a":
        text = read(workspace, "app.py") + tests
        require("parse_legacy" not in text, "obsolete parser fallback remains")
        require(app.load_items('{"items": [1, 2]}') == [1, 2], "current parser changed")
        with _raises(json.JSONDecodeError):
            app.load_items("one\ntwo\n")
    elif case_id == "f01b":
        require(app.load_items({"version": 2, "items": [1]}) == [1], "current protocol broke")
        require(app.load_items({"version": 1, "records": [2]}) == [2], "legacy protocol broke")
        with _raises(ValueError):
            app.load_items({"version": 0, "items": []})
    elif case_id == "f02a":
        require("except" not in read(workspace, "app.py"), "generic fallback remains")
        require(app.read_name({"name": "Ada"}) == "Ada", "valid name changed")
        with _raises(KeyError):
            app.read_name({})
    elif case_id == "f02b":
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"
            with _raises(RuntimeError):
                app.write_atomically(path, object(), lambda _value: (_ for _ in ()).throw(RuntimeError("failed")))
            require(not path.exists(), "failed write published output")
            require(not path.with_suffix(".bin.partial").exists(), "partial file leaked")
            app.write_atomically(path, "ok", lambda value: str(value).encode())
            require(path.read_bytes() == b"ok", "successful atomic write changed")
    else:
        raise KeyError(case_id)
    return "hidden focused behavior contract passed"


class _raises:
    def __init__(self, expected):
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            raise AssertionError(f"expected {self.expected.__name__}")
        if not issubclass(exc_type, self.expected):
            raise AssertionError(f"expected {self.expected.__name__}, got {exc_type.__name__}")
        return True


def source_metrics(root: Path) -> dict[str, int]:
    metrics = {
        "production_loc": 0,
        "test_loc": 0,
        "test_count": 0,
        "functions": 0,
        "classes": 0,
        "branches": 0,
        "try_blocks": 0,
        "except_handlers": 0,
        "checksum_mentions": 0,
        "verification_mentions": 0,
        "fallback_mentions": 0,
        "fixture_invocations": 0,
        "fallback_nodes": 0,
        "abstraction_nodes": 0,
    }
    for path in sorted(root.rglob("*.py")):
        text = path.read_text()
        lines = sum(bool(line.strip()) for line in text.splitlines())
        is_test = path.name.startswith("test_") or path.name.startswith("tests_")
        metrics["test_loc" if is_test else "production_loc"] += lines
        if is_test:
            metrics["test_count"] += sum(
                1 for node in ast.walk(ast.parse(text))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
            )
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                if not is_test and any(token in node.name.lower() for token in ("wrapper", "fallback", "adapter")):
                    metrics["abstraction_nodes"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                metrics["abstraction_nodes"] += 1
            elif isinstance(node, (ast.If, ast.IfExp, ast.For, ast.While, ast.Match)):
                metrics["branches"] += 1
            elif isinstance(node, (ast.Try, ast.TryStar)):
                metrics["try_blocks"] += 1
            elif isinstance(node, ast.ExceptHandler):
                metrics["except_handlers"] += 1
        lowered = text.lower()
        metrics["checksum_mentions"] += lowered.count("sha256") + lowered.count("checksum")
        metrics["verification_mentions"] += lowered.count("receipt") + lowered.count("manifest") + lowered.count("validate")
        metrics["fallback_mentions"] += lowered.count("fallback") + lowered.count("legacy") + lowered.count("except")
        metrics["fixture_invocations"] += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and any(token in node.func.id.lower() for token in ("fixture", "dataset", "load_records", "expensive"))
        )
        metrics["fallback_nodes"] += sum(
            1 for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
        )
    return metrics


def mini_behavior(repo: Path, category: str) -> str:
    if category == "test_bloat":
        app = module(repo, "reporting.py")
        expected = {"title": "run", "total": 2, "labels": ["alpha", "beta"]}
        require(app.publish_report(app.build_report("run", [{"label": " alpha "}, {"label": "beta"}])) == expected, "public report behavior changed")
    elif category == "verification_theater":
        app = module(repo, "reporting.py")
        expected = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            app.write_report(path, [{"value": 1}])
            require(app.read_persisted_report(path, expected) == [{"value": 1}], "persisted readback changed")
            path.write_text('{"records": [{"value": 9}]}')
            with _raises(ValueError):
                app.read_persisted_report(path, expected)
    elif category == "defensive_fallback_bloat":
        app = module(repo, "loader.py")
        require(app.load_versioned({"version": 2, "items": [1]}) == [1], "current protocol changed")
        require(app.load_versioned({"version": 1, "records": [2]}) == [2], "legacy protocol changed")
        with _raises(json.JSONDecodeError):
            app.load_items("not-json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"
            with _raises(RuntimeError):
                app.write_atomically(path, object(), lambda _value: (_ for _ in ()).throw(RuntimeError("failed")))
            require(not path.exists() and not path.with_suffix(".bin.partial").exists(), "atomic cleanup changed")
    else:
        raise KeyError(category)
    return "hidden mini-repository behavior gate passed"


def compare_mini_repositories(category: str, before: Path, after: Path) -> dict[str, object]:
    behavior = mini_behavior(after, category)
    before_tests = run_tests(before)
    after_tests = run_tests(after)
    before_metrics = source_metrics(before)
    after_metrics = source_metrics(after)
    delta = {key: after_metrics[key] - before_metrics[key] for key in before_metrics}
    delta["new_tests_added"] = max(delta["test_count"], 0)
    delta["new_wrappers_or_abstractions_added"] = max(delta["abstraction_nodes"], 0)
    delta["new_fallbacks_added"] = max(delta["fallback_nodes"], 0)
    return {
        "behavior_gate": {"passed": True, "evidence": behavior},
        "tests_before": before_tests,
        "tests_after": after_tests,
        "metrics_before": before_metrics,
        "metrics_after": after_metrics,
        "metric_delta_after_minus_before": delta,
    }


def hook_main() -> int:
    case_id = os.environ.get("ASE_EVAL_ID")
    workspace_name = os.environ.get("ASE_WORKSPACE_PATH")
    if not case_id or not workspace_name:
        return 2
    workspace = Path(workspace_name)
    rows = []
    try:
        evidence = case_contract(case_id, workspace)
        passed = True
    except Exception as error:
        passed = False
        evidence = f"{type(error).__name__}: {error}"
    rows.append({"text": f"focused hidden behavior for {case_id}", "passed": passed, "evidence": evidence})
    tests = run_tests(workspace)
    rows.append({"text": f"focused remaining tests for {case_id}", "passed": tests["passed"], "evidence": json.dumps(tests, sort_keys=True)})
    print(json.dumps(rows))
    return 0


def main() -> None:
    if len(sys.argv) == 1 and os.environ.get("ASE_EVAL_ID"):
        raise SystemExit(hook_main())
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    case_parser = subparsers.add_parser("case")
    case_parser.add_argument("case_id")
    case_parser.add_argument("workspace", type=Path)
    mini_parser = subparsers.add_parser("mini")
    mini_parser.add_argument("category", choices=("test_bloat", "verification_theater", "defensive_fallback_bloat"))
    mini_parser.add_argument("workspace", type=Path)
    metrics_parser = subparsers.add_parser("metrics")
    metrics_parser.add_argument("workspace", type=Path)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("category", choices=("test_bloat", "verification_theater", "defensive_fallback_bloat"))
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "case":
            evidence = case_contract(arguments.case_id, arguments.workspace)
            tests = run_tests(arguments.workspace)
        elif arguments.command == "mini":
            evidence = mini_behavior(arguments.workspace, arguments.category)
            tests = run_tests(arguments.workspace)
        else:
            evidence = "metrics collected"
            tests = None
        output = {"passed": True, "evidence": evidence, "remaining_tests": tests}
        if arguments.command == "metrics":
            output["metrics"] = source_metrics(arguments.workspace)
        elif arguments.command == "compare":
            output = {"passed": True, **compare_mini_repositories(arguments.category, arguments.before, arguments.after)}
    except Exception as error:
        output = {"passed": False, "evidence": f"{type(error).__name__}: {error}"}
    print(json.dumps(output, sort_keys=True))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
