"""昂贵 Web 查询的并发门与超时响应。"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from gpumon.api import query_control


@pytest.fixture(autouse=True)
def reset_gate():
    query_control._reset_query_gate_for_tests()
    yield
    query_control._reset_query_gate_for_tests()


def _settings(concurrency=1, wait_s=0):
    return SimpleNamespace(web=SimpleNamespace(
        max_query_concurrency=concurrency,
        query_queue_timeout_s=wait_s,
    ))


def test_full_query_gate_returns_generic_retryable_503(monkeypatch):
    monkeypatch.setattr(query_control, "load_settings", lambda: _settings())
    gate = query_control._get_query_gate()
    assert gate.semaphore.acquire(blocking=False)

    @query_control.bounded_query
    def query():
        raise AssertionError("满载时不应进入查询")

    try:
        with pytest.raises(HTTPException) as raised:
            query()
    finally:
        gate.semaphore.release()

    assert raised.value.status_code == 503
    assert raised.value.headers == {"Retry-After": "1"}


def test_sqlite_progress_interrupt_becomes_generic_503(monkeypatch):
    monkeypatch.setattr(query_control, "load_settings", lambda: _settings())

    @query_control.bounded_query
    def query():
        raise sqlite3.OperationalError("interrupted")

    with pytest.raises(HTTPException) as raised:
        query()

    assert raised.value.status_code == 503
    assert "SQLite" not in raised.value.detail


def test_unrelated_sqlite_errors_are_not_hidden(monkeypatch):
    monkeypatch.setattr(query_control, "load_settings", lambda: _settings())

    @query_control.bounded_query
    def query():
        raise sqlite3.OperationalError("database disk image is malformed")

    with pytest.raises(sqlite3.OperationalError, match="malformed"):
        query()
