#!/usr/bin/env python3
"""Versioned assertRaisesRegex recognition; all draft4 contracts/budgets stay fixed."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
IDENTITY = json.loads((ROOT / "revision.json").read_text())
BASE_PATH = ROOT.parents[1] / "dev-v3-evidence-edges" / "grade_evidence_edges.py"
if hashlib.sha256(BASE_PATH.read_bytes()).hexdigest() != IDENTITY["base_sha256"]:
    raise RuntimeError("The frozen draft4 grader identity changed")
spec = importlib.util.spec_from_file_location("edge_coverage_base", BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def raised_call_covered(workspace: Path, call_name: str) -> bool:
    for relative, path in base.python_files(workspace).items():
        if not base.is_test_path(relative):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            contexts = [getattr(item.context_expr.func, "id", getattr(item.context_expr.func, "attr", None))
                        for item in node.items if isinstance(item.context_expr, ast.Call)]
            if not set(contexts) & {"assertRaises", "assertRaisesRegex", "raises"}:
                continue
            for call in ast.walk(node):
                if not isinstance(call, ast.Call):
                    continue
                if getattr(call.func, "id", getattr(call.func, "attr", None)) == call_name:
                    return True
                if not isinstance(call.func, ast.Name):
                    continue
                parent = parents.get(call)
                while parent is not None and not isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if isinstance(parent, ast.For) and isinstance(parent.target, ast.Name) and parent.target.id == call.func.id:
                        if isinstance(parent.iter, (ast.Tuple, ast.List)):
                            names = {getattr(item, "id", getattr(item, "attr", None)) for item in parent.iter.elts}
                            if call_name in names:
                                return True
                        break
                    parent = parents.get(parent)
    return False


base.raised_call_covered = raised_call_covered


if __name__ == "__main__":
    if len(sys.argv) == 3:
        os.environ["ASE_EVAL_ID"] = sys.argv[1]
        os.environ["ASE_WORKSPACE_PATH"] = str(Path(sys.argv[2]).resolve())
    elif len(sys.argv) != 1:
        raise SystemExit("usage: grade.py [CASE_ID WORKSPACE]")
    raise SystemExit(base.hook_main())
