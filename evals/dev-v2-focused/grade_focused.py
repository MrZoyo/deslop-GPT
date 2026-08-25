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


CORPUS_ROOT = Path(__file__).resolve().parent
ADJUDICATION = json.loads((CORPUS_ROOT / "adjudication.json").read_text())
MICRO_REDUCTION_TARGETS = ADJUDICATION["micro_reduction_targets"]
MINI_REDUCTION_TARGETS = ADJUDICATION["mini_reduction_targets"]
NEGATIVE_CHANGE_LIMITS = ADJUDICATION["negative_change_budget"]
IGNORED_WORKSPACE_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
INSTALLED_SKILL_PREFIXES = {
    "claude-code": (".claude", "skills", "deslop"),
    "codex": (".agents", "skills", "deslop"),
    "fake": (".fake", "skills", "deslop"),
    "opencode": (".opencode", "skills", "deslop"),
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
LOCAL_VERIFICATION_TOKENS = (
    "envelope",
    "proof",
    "receipt",
)
HASH_CONSTRUCTORS = {
    "blake2b",
    "blake2s",
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
}
MINI_REPOSITORIES = {
    mini["id"]: (mini["category"], CORPUS_ROOT / mini["path"])
    for mini in ADJUDICATION["mini_repositories"]
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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

    if case_id == "t01a":
        require(app.summarize_records([{"name": "a"}]).names == ("a",), "summary behavior changed")
    elif case_id == "t01b":
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
        require(app.public_label("  Alpha   Beta ") == "alpha beta", "public label changed")
    elif case_id == "t02b":
        require(app.parse_header({"header": "v2"}) == "v2", "current header broke")
        require(app.parse_header({"legacy_header": "v1"}) == "v1", "legacy header broke")
    elif case_id == "t03a":
        require(app.normalize_identifier("  Device A  ") == "device-a", "identifier changed")
    elif case_id == "t03b":
        with _raises(ValueError):
            app.normalize_identifier("")
        require(app.normalize_identifier(" Straße ") == "strasse", "unicode normalization broke")
    elif case_id == "t04a":
        require(app.render_user("Ada") == "User: Ada", "renderer behavior changed")
    elif case_id == "t04b":
        require(app.export_wire_user("Ada") == b'USR/1 {"display": "User: Ada"}', "wire contract changed")
    elif case_id == "v01a":
        report = app.build_report([{"name": "a"}])
        require(report["records"] == [{"name": "a"}], "report behavior changed")
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
        require(app.load_items('{"items": [1, 2]}') == [1, 2], "current parser changed")
        with _raises(json.JSONDecodeError):
            app.load_items("one\ntwo\n")
    elif case_id == "f01b":
        require(app.load_items({"version": 2, "items": [1]}) == [1], "current protocol broke")
        require(app.load_items({"version": 1, "records": [2]}) == [2], "legacy protocol broke")
        with _raises(ValueError):
            app.load_items({"version": 0, "items": []})
    elif case_id == "f02a":
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


def reduction_target(case_id: str, workspace: Path) -> str:
    """Require a category-level target state, not an arbitrary one-line decrease."""
    if not case_id.endswith("a"):
        return "no deletion target for preservation case"
    before = source_metrics(CORPUS_ROOT / "files" / case_id)
    after = source_metrics(workspace)
    if case_id.startswith("t"):
        maximum = MICRO_REDUCTION_TARGETS["test_bloat"]["test_count_max"]
        require(after["test_count"] <= maximum, "test-bloat target requires at most one sufficient test")
    elif case_id.startswith("v"):
        target = MICRO_REDUCTION_TARGETS["verification_theater"]
        require(
            after["checksum_mentions"] <= target["checksum_mentions_max"]
            and after["local_verification_surface"] <= target["local_verification_surface_max"]
            and after["local_verifier_functions"] <= target["local_verifier_functions_max"]
            and after["hash_operations"] <= target["hash_operations_max"],
            "local verification cluster remains",
        )
    elif case_id.startswith("f"):
        target = MICRO_REDUCTION_TARGETS["defensive_fallback_bloat"]
        require(
            after["branches"] <= target["branches_max"]
            and after["try_blocks"] <= target["try_blocks_max"]
            and after["except_handlers"] <= target["except_handlers_max"],
            "fallback control-flow remains",
        )
    else:
        raise KeyError(case_id)
    return json.dumps(
        {"before": before, "after": after}, sort_keys=True, separators=(",", ":")
    )


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


def python_files(root: Path) -> dict[str, Path]:
    installed_skill_prefix = None
    if os.environ.get("ASE_WITH_SKILL") == "1":
        installed_skill_prefix = INSTALLED_SKILL_PREFIXES.get(os.environ.get("ASE_AGENT", ""))
    files = {}
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_WORKSPACE_PARTS for part in relative.parts):
            continue
        if (
            installed_skill_prefix is not None
            and relative.parts[: len(installed_skill_prefix)] == installed_skill_prefix
        ):
            continue
        files[relative.as_posix()] = path
    return files


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
        "catch_fallback_handlers": 0,
        "syntax_errors": 0,
        "checksum_mentions": 0,
        "verification_mentions": 0,
        "local_verification_surface": 0,
        "local_verifier_functions": 0,
        "hash_operations": 0,
        "fallback_mentions": 0,
        "fixture_invocations": 0,
        "fallback_nodes": 0,
        "abstraction_nodes": 0,
    }
    local_verification_tokens = set()
    for relative, path in sorted(python_files(root).items()):
        text = path.read_text()
        lines = sum(bool(line.strip()) for line in text.splitlines())
        relative_path = Path(relative)
        is_test = (
            relative_path.name.startswith("test_")
            or relative_path.name.startswith("tests_")
            or "tests" in relative_path.parts
        )
        metrics["test_loc" if is_test else "production_loc"] += lines
        try:
            tree = ast.parse(text)
        except SyntaxError:
            metrics["syntax_errors"] += 1
            continue
        if is_test:
            metrics["test_count"] += sum(
                1
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            )
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
                arguments = [
                    argument.arg
                    for argument in (*node.args.posonlyargs, *node.args.args)
                    if argument.arg not in {"self", "cls"}
                ]
                if (
                    not is_test
                    and any(token in node.name.lower() for token in ("validate", "verify"))
                    and len(arguments) <= 1
                ):
                    metrics["local_verifier_functions"] += 1
                if not is_test and any(token in node.name.lower() for token in ABSTRACTION_TOKENS):
                    metrics["abstraction_nodes"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                metrics["abstraction_nodes"] += 1
            elif isinstance(node, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.Match)):
                metrics["branches"] += 1
            elif isinstance(node, (ast.Try, ast.TryStar)):
                metrics["try_blocks"] += 1
            elif isinstance(node, ast.ExceptHandler):
                metrics["except_handlers"] += 1
                metrics["fallback_nodes"] += 1
                if any(isinstance(descendant, ast.Return) for descendant in ast.walk(node)):
                    metrics["catch_fallback_handlers"] += 1
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id.lower()
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr.lower()
                else:
                    call_name = ""
                hash_call = call_name in HASH_CONSTRUCTORS or (
                    call_name == "new"
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "hashlib"
                )
                if hash_call:
                    metrics["hash_operations"] += 1
        lowered = text.lower()
        local_verification_tokens.update(
            token for token in LOCAL_VERIFICATION_TOKENS if token in lowered
        )
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
    metrics["local_verification_surface"] = len(local_verification_tokens)
    return metrics


def imported_modules(root: Path) -> set[str]:
    modules = set()
    for path in python_files(root).values():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".", 1)[0])
    return modules


def negative_change_budget(
    fixture: Path,
    workspace: Path,
    category: str,
) -> tuple[bool, str]:
    before_files = python_files(fixture)
    after_files = python_files(workspace)
    new_python_files = sorted(set(after_files) - set(before_files))
    deleted_python_files = sorted(set(before_files) - set(after_files))
    new_dependencies = sorted(imported_modules(workspace) - imported_modules(fixture))
    before = source_metrics(fixture)
    after = source_metrics(workspace)
    delta = {key: after[key] - before[key] for key in before}
    positive_loc_growth = max(delta["production_loc"], 0) + max(delta["test_loc"], 0)
    target_metrics = {
        "test_bloat": ("test_count",),
        "verification_theater": (
            "checksum_mentions",
            "local_verification_surface",
            "local_verifier_functions",
            "hash_operations",
        ),
        "defensive_fallback_bloat": (
            "try_blocks",
            "except_handlers",
            "fallback_nodes",
            "catch_fallback_handlers",
        ),
    }[category]
    violations = []
    if len(new_python_files) > NEGATIVE_CHANGE_LIMITS["new_python_files_max"]:
        violations.append("new Python files")
    if after["syntax_errors"] > NEGATIVE_CHANGE_LIMITS["syntax_errors_max"]:
        violations.append("Python syntax errors")
    if delta["test_count"] > NEGATIVE_CHANGE_LIMITS["test_count_growth_max"]:
        violations.append("new tests")
    if positive_loc_growth > NEGATIVE_CHANGE_LIMITS["positive_python_loc_growth_max"]:
        violations.append("Python LOC growth")
    if delta["abstraction_nodes"] > NEGATIVE_CHANGE_LIMITS["abstraction_growth_max"]:
        violations.append("new wrappers or abstractions")
    if len(new_dependencies) > NEGATIVE_CHANGE_LIMITS["new_dependencies_max"]:
        violations.append("new dependencies")
    if any(
        delta[key] > NEGATIVE_CHANGE_LIMITS["category_target_growth_max"]
        for key in target_metrics
    ):
        violations.append("new category-target machinery")
    evidence = (
        f"nonblank_python_line_delta={delta['production_loc'] + delta['test_loc']}; "
        f"positive_python_loc_growth={positive_loc_growth}; "
        f"new_python_files={new_python_files}; deleted_python_files={deleted_python_files}; "
        f"new_dependencies={new_dependencies}; "
        f"metric_delta={json.dumps(delta, sort_keys=True, separators=(',', ':'))}; "
        f"violations={violations}"
    )
    return not violations, evidence


def case_category(case_id: str) -> str:
    return {
        "t": "test_bloat",
        "v": "verification_theater",
        "f": "defensive_fallback_bloat",
    }[case_id[0]]


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
    before_tests = run_tests(before)
    after_tests = run_tests(after)
    require(after_tests["passed"], f"remaining test suite failed: {after_tests}")
    behavior = mini_behavior(after, category)
    before_metrics = source_metrics(before)
    after_metrics = source_metrics(after)
    delta = {key: after_metrics[key] - before_metrics[key] for key in before_metrics}
    delta["new_tests_added"] = max(delta["test_count"], 0)
    delta["new_wrappers_or_abstractions_added"] = max(delta["abstraction_nodes"], 0)
    delta["new_fallbacks_added"] = max(delta["fallback_nodes"], 0)
    comparison = {
        "behavior_gate": {"passed": True, "evidence": behavior},
        "eligible_for_reduction_scoring": True,
        "tests_before": before_tests,
        "tests_after": after_tests,
        "metrics_before": before_metrics,
        "metrics_after": after_metrics,
        "metric_delta_after_minus_before": delta,
    }
    try:
        target_evidence = mini_reduction_target(category, before_metrics, after_metrics)
        target_passed = True
    except Exception as error:
        target_passed = False
        target_evidence = f"{type(error).__name__}: {error}"
    budget_passed, budget_evidence = negative_change_budget(before, after, category)
    comparison["reduction_target"] = {
        "passed": target_passed,
        "evidence": target_evidence,
    }
    comparison["negative_change_budget"] = {
        "passed": budget_passed,
        "evidence": budget_evidence,
    }
    return comparison


def mini_reduction_target(
    category: str,
    before: dict[str, int],
    after: dict[str, int],
) -> str:
    if category == "test_bloat":
        target = MINI_REDUCTION_TARGETS[category]
        require(
            within_fraction(after["test_count"], before["test_count"], target["test_count_fraction_max"]),
            "test count was not cut by at least half",
        )
        require(
            within_fraction(after["test_loc"], before["test_loc"], target["test_loc_fraction_max"]),
            "test LOC was not cut by at least half",
        )
        require(
            within_fraction(
                after["fixture_invocations"],
                before["fixture_invocations"],
                target["fixture_invocations_fraction_max"],
            ),
            "fixture invocations were not cut by at least half",
        )
    elif category == "verification_theater":
        target = MINI_REDUCTION_TARGETS[category]
        require(
            after["local_verification_surface"] <= target["local_verification_surface_max"],
            "local receipt/validator/checksum surface remains",
        )
        require(
            after["local_verifier_functions"] <= target["local_verifier_functions_max"],
            "single-input local verifier remains",
        )
        require(
            after["hash_operations"] <= target["hash_operations_max"],
            "self-generated hash operation remains outside the readback boundary",
        )
        require(
            within_fraction(
                after["checksum_mentions"],
                before["checksum_mentions"],
                target["checksum_mentions_fraction_max"],
            ),
            "checksum surface was not cut by at least half",
        )
    elif category == "defensive_fallback_bloat":
        target = MINI_REDUCTION_TARGETS[category]
        require(
            (not target["try_blocks_must_decrease"] or after["try_blocks"] < before["try_blocks"])
            and (
                not target["except_handlers_must_decrease"]
                or after["except_handlers"] < before["except_handlers"]
            )
            and after["try_blocks"] <= target["try_blocks_max"],
            "parser catch/fallback layer remains",
        )
        require(
            after["catch_fallback_handlers"] <= target["catch_fallback_handlers_max"],
            "catch-and-return fallback remains",
        )
    else:
        raise KeyError(category)
    return json.dumps(
        {"before": before, "after": after}, sort_keys=True, separators=(",", ":")
    )


def within_fraction(after: int, before: int, fraction: str) -> bool:
    numerator, denominator = (int(part) for part in fraction.split("/", 1))
    return after * denominator <= before * numerator


def hook_main() -> int:
    case_id = os.environ.get("ASE_EVAL_ID")
    workspace_name = os.environ.get("ASE_WORKSPACE_PATH")
    if not case_id or not workspace_name:
        return 2
    workspace = Path(workspace_name)
    rows = []
    if case_id in MINI_REPOSITORIES:
        category, fixture = MINI_REPOSITORIES[case_id]
        workspace = workspace / fixture.relative_to(CORPUS_ROOT)
        tests = run_tests(workspace)
        try:
            behavior_evidence = mini_behavior(workspace, category)
            behavior_passed = True
        except Exception as error:
            behavior_passed = False
            behavior_evidence = f"{type(error).__name__}: {error}"
        rows.append(
            {
                "text": f"focused hidden behavior for {case_id}",
                "passed": behavior_passed,
                "evidence": behavior_evidence,
            }
        )
        rows.append(
            {
                "text": f"focused remaining tests for {case_id}",
                "passed": tests["passed"],
                "evidence": json.dumps(tests, sort_keys=True),
            }
        )
        if behavior_passed and tests["passed"]:
            comparison = compare_mini_repositories(category, fixture, workspace)
            target = comparison["reduction_target"]
            budget = comparison["negative_change_budget"]
        else:
            ineligible = "ineligible until behavior and remaining-test gates pass"
            target = {"passed": False, "evidence": ineligible}
            budget_passed, budget_evidence = negative_change_budget(fixture, workspace, category)
            budget = {"passed": budget_passed, "evidence": budget_evidence}
        rows.append(
            {
                "text": f"focused reduction target for {case_id}",
                "passed": target["passed"],
                "evidence": target["evidence"],
            }
        )
        rows.append(
            {
                "text": f"negative-change budget for {case_id}",
                "passed": budget["passed"],
                "evidence": budget["evidence"],
            }
        )
        print(json.dumps(rows))
        return 0

    try:
        evidence = case_contract(case_id, workspace)
        passed = True
    except Exception as error:
        passed = False
        evidence = f"{type(error).__name__}: {error}"
    rows.append({"text": f"focused hidden behavior for {case_id}", "passed": passed, "evidence": evidence})
    tests = run_tests(workspace)
    rows.append({"text": f"focused remaining tests for {case_id}", "passed": tests["passed"], "evidence": json.dumps(tests, sort_keys=True)})
    if case_id.endswith("a"):
        if passed and tests["passed"]:
            try:
                reduction_evidence = reduction_target(case_id, workspace)
                reduction_passed = True
            except Exception as error:
                reduction_passed = False
                reduction_evidence = f"{type(error).__name__}: {error}"
        else:
            reduction_passed = False
            reduction_evidence = "ineligible until behavior and remaining-test gates pass"
        rows.append({"text": f"focused reduction target for {case_id}", "passed": reduction_passed, "evidence": reduction_evidence})
    budget_passed, budget_evidence = negative_change_budget(
        CORPUS_ROOT / "files" / case_id,
        workspace,
        case_category(case_id),
    )
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
            target = None
            if arguments.case_id.endswith("a"):
                target = reduction_target(arguments.case_id, arguments.workspace)
        elif arguments.command == "mini":
            evidence = mini_behavior(arguments.workspace, arguments.category)
            tests = run_tests(arguments.workspace)
            target = None
        else:
            evidence = "metrics collected"
            tests = None
            target = None
        output = {"passed": True, "evidence": evidence, "remaining_tests": tests}
        if target is not None:
            output["reduction_target"] = target
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
