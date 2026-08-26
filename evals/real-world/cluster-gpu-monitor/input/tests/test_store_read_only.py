"""Web Store 的 SQLite 只读边界。"""

import sqlite3
from types import SimpleNamespace

import pytest

from gpumon.api import deps
from gpumon.db import store as store_module
from gpumon.db.store import Store


def _seed(path):
    store = Store(path=path)
    store.init_schema()
    store.write_conn().execute(
        "INSERT INTO cluster(key, name, sort_order) VALUES(?, ?, ?)",
        ("demo", "Demo", 0),
    )
    store.write_conn().commit()
    return store


def test_read_only_store_can_query_but_cannot_write(tmp_path):
    path = tmp_path / "monitor.db"
    writer = _seed(path)
    reader = Store(path=path, read_only=True)

    with reader.connect() as conn:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        assert conn.execute("SELECT name FROM cluster").fetchone()[0] == "Demo"
        with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
            conn.execute(
                "INSERT INTO cluster(key, name, sort_order) VALUES('bad', 'Bad', 1)"
            )
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")

    # 保持写连接存活，覆盖生产中 collector 写、Web 并发读的 WAL 场景。
    assert writer.write_conn().execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    with pytest.raises(RuntimeError, match="只读 Store"):
        reader.write_conn()
    with pytest.raises(RuntimeError, match="只读 Store"):
        reader.init_schema()


def test_query_connection_closes_when_context_body_raises(tmp_path):
    path = tmp_path / "monitor.db"
    _seed(path)
    reader = Store(path=path, read_only=True)

    with pytest.raises(RuntimeError, match="stop"):
        with reader.connect() as conn:
            raise RuntimeError("stop")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")


def test_read_only_store_does_not_create_missing_database_or_parent(tmp_path):
    path = tmp_path / "missing-parent" / "missing.db"

    with pytest.raises(sqlite3.OperationalError):
        Store(path=path, read_only=True).connect()

    assert not path.exists()
    assert not path.parent.exists()


def test_read_only_store_interrupts_queries_after_deadline(tmp_path):
    path = tmp_path / "monitor.db"
    _seed(path)
    reader = Store(path=path, read_only=True, query_timeout_s=0)

    with reader.connect() as conn:
        with pytest.raises(sqlite3.OperationalError, match="interrupted"):
            conn.execute("""
                WITH RECURSIVE n(x) AS (
                    VALUES(1) UNION ALL SELECT x + 1 FROM n WHERE x < 1000000
                )
                SELECT SUM(x) FROM n
            """).fetchone()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")


def test_api_dependency_constructs_read_only_store(tmp_path, monkeypatch):
    deps.get_store.cache_clear()
    monkeypatch.setattr(store_module, "db_path", lambda: tmp_path / "api.db")
    monkeypatch.setattr(
        deps,
        "load_settings",
        lambda: SimpleNamespace(web=SimpleNamespace(query_timeout_s=12)),
    )
    try:
        store = deps.get_store()
        assert store.read_only is True
        assert store.query_timeout_s == 12
    finally:
        deps.get_store.cache_clear()
