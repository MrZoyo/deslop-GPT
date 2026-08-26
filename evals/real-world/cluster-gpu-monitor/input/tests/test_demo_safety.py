"""Demo 生成/静态导出不得覆盖或误导出真实文件。"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.append(str(SCRIPTS))

import export_static_demo  # noqa: E402
import gen_demo_db  # noqa: E402
from demo_safety import (  # noqa: E402
    DEMO_INVENTORY_MARKER,
    DemoSafetyError,
    REPO_ROOT,
    assert_safe_export_directory,
    demo_database_state,
    safe_child,
    static_output_is_marked,
)


@pytest.mark.parametrize("dangerous", [Path("/"), Path.home(), REPO_ROOT, REPO_ROOT / "web/js"])
def test_static_export_rejects_dangerous_output_directories(dangerous):
    with pytest.raises(DemoSafetyError):
        assert_safe_export_directory(dangerous)


def test_safe_child_rejects_output_escape(tmp_path):
    with pytest.raises(DemoSafetyError):
        safe_child(tmp_path, "../outside.json")
    assert safe_child(tmp_path, "api/inside.json").is_relative_to(tmp_path)


def test_generator_refuses_real_names_even_with_force(tmp_path):
    real_named_db = tmp_path / "gpumon.db"
    real_named_db.write_bytes(b"must stay")
    inventory = tmp_path / "inventory.demo.yaml"

    rc = gen_demo_db.main([
        "--db", str(real_named_db),
        "--inventory", str(inventory),
        "--days", "0",
        "--force",
        "--quiet",
    ])

    assert rc == 2
    assert real_named_db.read_bytes() == b"must stay"
    assert not inventory.exists()


def test_generator_refuses_to_overwrite_unmarked_files(tmp_path):
    db = tmp_path / "demo.db"
    inventory = tmp_path / "inventory.demo.yaml"
    db.write_bytes(b"not a demo database")
    inventory.write_text("not a demo inventory\n", encoding="utf-8")

    rc = gen_demo_db.main([
        "--db", str(db),
        "--inventory", str(inventory),
        "--days", "0",
        "--force",
        "--quiet",
    ])

    assert rc == 2
    assert db.read_bytes() == b"not a demo database"
    assert inventory.read_text(encoding="utf-8") == "not a demo inventory\n"


def test_generated_demo_is_marked_and_exportable(tmp_path):
    db = tmp_path / "synthetic-demo.db"
    inventory = tmp_path / "inventory.demo.yaml"
    out = tmp_path / "static-demo"

    generated = gen_demo_db.main([
        "--db", str(db),
        "--inventory", str(inventory),
        "--days", "0",
        "--quiet",
    ])
    export_run = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "export_static_demo.py"),
            "--db", str(db),
            "--inventory", str(inventory),
            "--settings", str(REPO_ROOT / "config/settings.example.toml"),
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert generated == 0
    assert demo_database_state(db) == "complete"
    assert inventory.read_text(encoding="utf-8").startswith(DEMO_INVENTORY_MARKER + "\n")
    assert export_run.returncode == 0, export_run.stderr
    assert static_output_is_marked(out)
    assert (out / "index.html").is_file()
    assert (out / "api/live.json").read_text(encoding="utf-8") == '{"ok":true,"status":"alive"}'
    inventory_data = yaml.safe_load(inventory.read_text(encoding="utf-8"))
    assert inventory_data["badge_library"][0]["text"] == {
        "zh": "自建",
        "en": "Self-built",
    }
    meta = json.loads((out / "api/meta.json").read_text(encoding="utf-8"))
    group = meta["capacity_groups"][0]
    assert group["description"] == "自建机房。空调是去年双十一买的，夏天限功耗跑。"
    assert list(group["description_i18n"]) == ["zh", "en"]


def test_static_export_rejects_unmarked_database_without_deleting_output(tmp_path):
    db = tmp_path / "unmarked.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE harmless(value TEXT)")
    inventory = tmp_path / "inventory.demo.yaml"
    inventory.write_text(DEMO_INVENTORY_MARKER + "\nversion: 1\nclusters: []\n", encoding="utf-8")
    out = tmp_path / "existing-output"
    out.mkdir()
    sentinel = out / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    rc = export_static_demo.main([
        "--db", str(db),
        "--inventory", str(inventory),
        "--settings", str(REPO_ROOT / "config/settings.example.toml"),
        "--out", str(out),
        "--force",
    ])

    assert rc == 2
    assert sentinel.read_text(encoding="utf-8") == "keep"
