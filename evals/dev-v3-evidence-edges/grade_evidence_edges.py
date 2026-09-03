#!/usr/bin/env python3
"""Hidden-contract grader for the dev-v3 evidence-edge draft."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


sys.dont_write_bytecode = True

CORPUS_ROOT = Path(__file__).resolve().parent
ADJUDICATION = json.loads((CORPUS_ROOT / "adjudication.json").read_text())
CASES = {case["id"]: case for case in ADJUDICATION["cases"]}
LIMITS = ADJUDICATION["negative_change_budget"]
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
INSTALLED_SKILL_PREFIXES = {
    (".agents", "skills", "deslop"),
    (".claude", "skills", "deslop"),
    (".fake", "skills", "deslop"),
    (".opencode", "skills", "deslop"),
}
ABSTRACTION_TOKENS = (
    "adapter",
    "factory",
    "manager",
    "protocol",
    "provider",
    "registry",
    "validator",
    "wrapper",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class raises:
    def __init__(self, expected):
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            names = ", ".join(item.__name__ for item in self._types())
            raise AssertionError(f"expected one of: {names}")
        if not issubclass(exc_type, self._types()):
            return False
        return True

    def _types(self):
        return self.expected if isinstance(self.expected, tuple) else (self.expected,)


def module(workspace: Path):
    path = workspace / "app.py"
    module_name = f"evidence_edges_{abs(hash(path.resolve()))}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def run_tests(workspace: Path) -> dict[str, object]:
    started = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
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
        words = line.strip().split()
        if len(words) >= 2 and words[0] == "Ran" and words[1].isdigit():
            count = int(words[1])
            break
    return {
        "passed": result.returncode == 0 and count > 0,
        "count": count,
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "output": output if result.returncode else "",
    }


def ignored(relative: Path) -> bool:
    if any(part in IGNORED_PARTS for part in relative.parts):
        return True
    return any(relative.parts[: len(prefix)] == prefix for prefix in INSTALLED_SKILL_PREFIXES)


def workspace_files(root: Path) -> dict[str, Path]:
    files = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if not ignored(relative):
            files[relative.as_posix()] = path
    return files


def python_files(root: Path) -> dict[str, Path]:
    return {
        relative: path
        for relative, path in workspace_files(root).items()
        if path.suffix == ".py"
    }


def is_test_path(relative: str) -> bool:
    path = Path(relative)
    return path.name.startswith(("test_", "tests_")) or "tests" in path.parts


def source_metrics(root: Path) -> dict[str, int]:
    metrics = {
        "production_loc": 0,
        "test_loc": 0,
        "test_count": 0,
        "functions": 0,
        "classes": 0,
        "branches": 0,
        "syntax_errors": 0,
        "abstraction_nodes": 0,
    }
    for relative, path in sorted(python_files(root).items()):
        text = path.read_text()
        loc = sum(bool(line.strip()) for line in text.splitlines())
        test_file = is_test_path(relative)
        metrics["test_loc" if test_file else "production_loc"] += loc
        try:
            tree = ast.parse(text)
        except SyntaxError:
            metrics["syntax_errors"] += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                if test_file and node.name.startswith("test_"):
                    metrics["test_count"] += 1
                if not test_file and any(token in node.name.lower() for token in ABSTRACTION_TOKENS):
                    metrics["abstraction_nodes"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                if not test_file:
                    metrics["abstraction_nodes"] += 1
            elif isinstance(node, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.Match)):
                metrics["branches"] += 1
    return metrics


def imported_external_modules(root: Path) -> set[str]:
    local_modules = {path.stem for path in python_files(root).values()}
    modules = set()
    for path in python_files(root).values():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".", 1)[0]}
            else:
                continue
            modules.update(
                name
                for name in names
                if name not in sys.stdlib_module_names and name not in local_modules
            )
    return modules


def negative_change_budget(fixture: Path, workspace: Path, action: str) -> tuple[bool, str]:
    before_files = workspace_files(fixture)
    after_files = workspace_files(workspace)
    new_files = sorted(set(after_files) - set(before_files))
    before = source_metrics(fixture)
    after = source_metrics(workspace)
    delta = {key: after[key] - before[key] for key in before}
    positive_python_growth = max(
        delta["production_loc"] + delta["test_loc"],
        0,
    )
    new_dependencies = sorted(
        imported_external_modules(workspace) - imported_external_modules(fixture)
    )
    violations = []
    if len(new_files) > LIMITS["new_files_max"]:
        violations.append("new files")
    if delta["test_count"] > LIMITS["test_count_growth_max"]:
        violations.append("new tests")
    if len(new_dependencies) > LIMITS["new_external_dependencies_max"]:
        violations.append("new external dependencies")
    if delta["abstraction_nodes"] > LIMITS["abstraction_growth_max"]:
        violations.append("new abstractions")
    if after["syntax_errors"] > LIMITS["syntax_errors_max"]:
        violations.append("Python syntax errors")
    maximum_growth = LIMITS["positive_python_loc_growth_max"][action]
    if positive_python_growth > maximum_growth:
        violations.append("Python LOC growth")
    evidence = (
        f"action={action}; new_files={new_files}; new_external_dependencies={new_dependencies}; "
        f"positive_python_loc_growth={positive_python_growth}; "
        f"metric_delta={json.dumps(delta, sort_keys=True, separators=(',', ':'))}; "
        f"violations={violations}"
    )
    return not violations, evidence


def python_text(workspace: Path) -> str:
    return "\n".join(path.read_text().casefold() for path in python_files(workspace).values())


def integration_root_present(workspace: Path, call_name: str) -> bool:
    for relative, path in python_files(workspace).items():
        if not is_test_path(relative):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == call_name:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == call_name:
                return True
    return False


def raised_call_covered(workspace: Path, call_name: str) -> bool:
    for relative, path in python_files(workspace).items():
        if not is_test_path(relative):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            contexts = []
            for item in node.items:
                expression = item.context_expr
                if not isinstance(expression, ast.Call):
                    continue
                if isinstance(expression.func, ast.Name):
                    contexts.append(expression.func.id)
                elif isinstance(expression.func, ast.Attribute):
                    contexts.append(expression.func.attr)
            if not any(name in {"assertRaises", "raises"} for name in contexts):
                continue
            for descendant in ast.walk(node):
                if not isinstance(descendant, ast.Call):
                    continue
                if isinstance(descendant.func, ast.Name) and descendant.func.id == call_name:
                    return True
                if isinstance(descendant.func, ast.Attribute) and descendant.func.attr == call_name:
                    return True
    return False


def copy_visible_workspace(source: Path, destination: Path) -> None:
    for relative, path in workspace_files(source).items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def require_hermetic_builder_test(workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        copied = Path(directory) / "case"
        copied.mkdir()
        copy_visible_workspace(workspace, copied)
        compiled = copied / "compiled.json"
        sentinel = b'user-owned tracked edit\n'
        compiled.write_bytes(sentinel)
        tests = run_tests(copied)
        require(tests["passed"], f"copied test suite failed: {tests['output']}")
        require(compiled.read_bytes() == sentinel, "test overwrote tracked compiled.json")


def basic_behavior(case_id: str, workspace: Path) -> None:
    app = module(workspace)
    if case_id == "r01a":
        require(app.active_camera() == {"name": "front", "parent": "head"}, "active camera changed")
    elif case_id == "r01b":
        require(
            app.camera_from_active_config("left") == {"name": "left", "parent": "left_wrist"},
            "left active camera changed",
        )
        require(
            app.camera_from_active_config("right") == {"name": "right", "parent": "right_wrist"},
            "right active camera changed",
        )
    elif case_id == "r02a":
        require(
            app.summarize_current([2, 3]) == {"count": 2, "total": 5},
            "current summary changed",
        )
    elif case_id == "r02b":
        require(app.run_current_episode("TASK-CURRENT-03") is True, "current production path changed")
    elif case_id == "h01a":
        require(app.public_label({"name": " Alpha "}) == "alpha", "public label changed")
    elif case_id == "h01b":
        fixture = workspace / "fixtures" / "protocol.json"
        require(
            app.load_protocol_fixture(fixture) == ("rgb", "depth", "mask"),
            "managed protocol fixture changed",
        )
    elif case_id in {"h02a", "h02b"}:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text((workspace / "source.json").read_text())
            (root / "config.json").write_text(
                json.dumps({"source": "source.json", "output": "built.json"})
            )
            require(
                app.build_assets(root / "config.json")
                == {"joint": "hinge", "collision": "door-panel"},
                "asset compilation changed",
            )
    elif case_id == "v03a":
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = b'{"release": "r1"}'
            (root / "artifact.json").write_bytes(artifact)
            (root / "component.json").write_text(json.dumps({"parts": 47}))
            descriptor = {
                "artifact": "artifact.json",
                "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
            }
            require(app.load_package(root, descriptor) == {"parts": 47}, "package load changed")
    elif case_id == "v03b":
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.json").write_text(json.dumps({"status": "ok"}))
            (root / "preview.txt").write_text("frame 1")
            descriptor = {"report": "report.json", "optional_preview": "preview.txt"}
            require(
                app.load_report(root, descriptor) == ({"status": "ok"}, "frame 1"),
                "available preview behavior changed",
            )
    elif case_id == "s01a":
        payload = {"schema": "2.0", "storage": "video", "frames": ["a", "b"]}
        require(app.load_episode(payload) == ("a", "b"), "current loader changed")
        require(app.montage_frames(payload) == ("a", "b"), "current montage changed")
    elif case_id == "s01b":
        require(
            app.migrate_episode({"schema": "2.0", "frames": ["a"]})
            == {"schema": "2.0", "frames": ["a"]},
            "current migration input changed",
        )
    elif case_id == "s02a":
        task = app.parse_task({"component_package": "outputs/current-grasp-ready"})
        require(task.component_package == "outputs/current-grasp-ready", "explicit package changed")
    elif case_id == "s02b":
        options = app.parse_report_options({"display_label": "nightly"})
        require(options.display_label == "nightly", "explicit label changed")
    else:
        raise KeyError(case_id)


def required_artifact_contract(workspace: Path) -> None:
    app = module(workspace)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        artifact = b'{"release": "r1"}'
        artifact_path = root / "artifact.json"
        artifact_path.write_bytes(artifact)
        (root / "component.json").write_text(json.dumps({"parts": 47}))
        descriptor = {
            "artifact": "artifact.json",
            "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
        }
        artifact_path.unlink()
        with raises((FileNotFoundError, ValueError)):
            app.load_package(root, descriptor)
        artifact_path.write_bytes(b"tampered")
        with raises(ValueError):
            app.load_package(root, descriptor)


def preservation_contract(case_id: str, workspace: Path) -> None:
    app = module(workspace)
    if case_id == "r01b":
        return
    if case_id == "r02b":
        require(
            integration_root_present(workspace, "run_current_episode"),
            "no test crosses the current public production path",
        )
    elif case_id == "h01b":
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(json.dumps({"schema": "sensor-protocol-1", "channels": ["rgb"]}))
            with raises(ValueError):
                app.load_protocol_fixture(path)
    elif case_id == "h02b":
        require_hermetic_builder_test(workspace)
    elif case_id == "v03b":
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.json").write_text(json.dumps({"status": "ok"}))
            expected = ({"status": "ok"}, None)
            require(app.load_report(root, {"report": "report.json"}) == expected, "missing optional key failed")
            descriptor = {"report": "report.json", "optional_preview": "missing.txt"}
            require(app.load_report(root, descriptor) == expected, "missing optional file failed")
    elif case_id == "s01b":
        require(
            app.migrate_episode({"schema": "1.0", "images": ["old"]})
            == {"schema": "2.0", "frames": ["old"]},
            "documented legacy migration changed",
        )
        with raises(ValueError):
            app.migrate_episode({"schema": "0.9", "images": []})
    elif case_id == "s02b":
        require(
            app.parse_report_options({}).display_label == "untitled",
            "optional display label default changed",
        )
    else:
        raise KeyError(case_id)


def case_contract(case_id: str, workspace: Path) -> str:
    basic_behavior(case_id, workspace)
    if case_id.endswith("b"):
        preservation_contract(case_id, workspace)
    return "current behavior and preservation contract passed"


def case_target(case_id: str, workspace: Path) -> str:
    require(case_id.endswith("a"), "only positive cases have a target")
    text = python_text(workspace)
    metrics = source_metrics(workspace)
    if case_id == "r01a":
        require("future_left" not in text, "future-only camera surface remains")
        require(metrics["test_count"] <= 1, "future-only test remains")
        require(integration_root_present(workspace, "active_camera"), "active behavior lacks a test root")
    elif case_id == "r02a":
        require("legacy" not in text, "legacy package path remains")
        require(metrics["test_count"] <= 1, "legacy package test remains")
        require(
            integration_root_present(workspace, "summarize_current"),
            "current summary lacks a test root",
        )
    elif case_id == "h01a":
        require("legacy_product" not in text, "test-owned production helper remains")
        require("outputs" not in text and "skipunless" not in text, "unmanaged output test remains")
        require(metrics["test_count"] <= 1, "unmanaged output test remains")
        require(integration_root_present(workspace, "public_label"), "public label lacks a test root")
    elif case_id == "h02a":
        require_hermetic_builder_test(workspace)
        require(integration_root_present(workspace, "build_assets"), "builder lacks an integration test")
    elif case_id == "v03a":
        required_artifact_contract(workspace)
        require(
            raised_call_covered(workspace, "load_package"),
            "missing authoritative artifact lacks a visible negative test",
        )
    elif case_id == "s01a":
        app = module(workspace)
        old = {"schema": "1.0", "storage": "video", "frames": ["old"]}
        with raises(ValueError):
            app.montage_frames(old)
        require(
            raised_call_covered(workspace, "montage_frames"),
            "old-schema montage behavior lacks a visible negative test",
        )
    elif case_id == "s02a":
        app = module(workspace)
        with raises((KeyError, ValueError, TypeError)):
            app.parse_task({})
        require("old-component-catalog" not in text, "historical identity default remains")
        require(
            raised_call_covered(workspace, "parse_task"),
            "missing required field lacks a visible negative test",
        )
    else:
        raise KeyError(case_id)
    return "positive cleanup or fail-visible correction target passed"


def hook_main() -> int:
    case_id = os.environ.get("ASE_EVAL_ID")
    workspace_name = os.environ.get("ASE_WORKSPACE_PATH")
    if case_id not in CASES or not workspace_name:
        return 2
    workspace = Path(workspace_name)
    rows = []
    try:
        evidence = case_contract(case_id, workspace)
        behavior_passed = True
    except Exception as error:
        behavior_passed = False
        evidence = f"{type(error).__name__}: {error}"
    rows.append(
        {
            "text": f"evidence-edge behavior and preservation contract for {case_id}",
            "passed": behavior_passed,
            "evidence": evidence,
        }
    )
    tests = run_tests(workspace)
    rows.append(
        {
            "text": f"evidence-edge remaining tests for {case_id}",
            "passed": tests["passed"],
            "evidence": json.dumps({key: value for key, value in tests.items() if key != "output"}, sort_keys=True),
        }
    )
    if case_id.endswith("a"):
        if behavior_passed and tests["passed"]:
            try:
                target_evidence = case_target(case_id, workspace)
                target_passed = True
            except Exception as error:
                target_passed = False
                target_evidence = f"{type(error).__name__}: {error}"
        else:
            target_passed = False
            target_evidence = "ineligible until behavior and remaining-test gates pass"
        rows.append(
            {
                "text": f"evidence-edge target for {case_id}",
                "passed": target_passed,
                "evidence": target_evidence,
            }
        )
    fixture = CORPUS_ROOT / "files" / case_id
    action = CASES[case_id]["expected"]
    budget_passed, budget_evidence = negative_change_budget(fixture, workspace, action)
    rows.append(
        {
            "text": f"negative-change budget for {case_id}",
            "passed": budget_passed,
            "evidence": budget_evidence,
        }
    )
    print(json.dumps(rows))
    return 0


def main() -> None:
    if len(sys.argv) == 1 and os.environ.get("ASE_EVAL_ID"):
        raise SystemExit(hook_main())
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    case_parser = subparsers.add_parser("case")
    case_parser.add_argument("case_id", choices=sorted(CASES))
    case_parser.add_argument("workspace", type=Path)
    target_parser = subparsers.add_parser("target")
    target_parser.add_argument("case_id", choices=sorted(CASES))
    target_parser.add_argument("workspace", type=Path)
    metrics_parser = subparsers.add_parser("metrics")
    metrics_parser.add_argument("workspace", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "case":
            evidence = case_contract(arguments.case_id, arguments.workspace)
            output = {
                "passed": True,
                "evidence": evidence,
                "remaining_tests": run_tests(arguments.workspace),
            }
        elif arguments.command == "target":
            evidence = case_target(arguments.case_id, arguments.workspace)
            output = {"passed": True, "evidence": evidence}
        else:
            output = {"passed": True, "metrics": source_metrics(arguments.workspace)}
    except Exception as error:
        output = {"passed": False, "evidence": f"{type(error).__name__}: {error}"}
    print(json.dumps(output, sort_keys=True))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()
