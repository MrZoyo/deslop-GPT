"""API 输入边界与 readiness/liveness 语义回归测试。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import gpumon.api.routes as routes
from gpumon.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/api/overview?window=forever",
        "/api/metrics/avg?window=forever",
        "/api/metrics/avg?scope=wrong",
        "/api/metrics/avg?metric=wrong",
        "/api/metrics/avg_multi?scope=wrong",
        "/api/metrics/avg_multi?metric=wrong",
        "/api/metrics/series?scope=wrong&id=1",
        "/api/metrics/series?scope=gpu",
        "/api/metrics/series?scope=global&id=1",
        "/api/metrics/series?scope=gpu&id=0",
        "/api/metrics/series?scope=gpu&id=not-an-int",
        "/api/users/top?window=forever",
        "/api/users/top?by=wrong",
        "/api/users/ranking?window=forever",
    ],
)
def test_invalid_query_parameters_are_explicit_4xx(client, path):
    response = client.get(path)
    assert 400 <= response.status_code < 500, response.text


def test_health_config_failure_is_generic_503_but_live_stays_up(client, monkeypatch):
    def broken_settings():
        raise RuntimeError("sensitive configuration detail")

    monkeypatch.setattr(routes, "load_settings", broken_settings)

    health = client.get("/api/health")
    live = client.get("/api/live")

    assert health.status_code == 503
    assert health.json() == {
        "ok": False,
        "status": "unavailable",
        "error": "configuration unavailable",
    }
    assert "sensitive" not in health.text
    assert live.status_code == 200
    assert live.json() == {"ok": True, "status": "alive"}


def test_health_database_failure_is_generic_503(client, monkeypatch):
    class BrokenStore:
        def connect(self):
            raise RuntimeError("database path and secret detail")

    monkeypatch.setattr(routes, "load_settings", lambda: object())
    monkeypatch.setattr(routes, "load_inventory", lambda: object())
    monkeypatch.setattr(routes, "get_store", lambda: BrokenStore())

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "ok": False,
        "status": "unavailable",
        "error": "database unavailable",
    }
    assert "secret" not in response.text


@pytest.mark.parametrize(
    ("last_sample", "expected_ok", "expected_status", "expected_age"),
    [
        (950, True, "ok", 50),
        (800, False, "stale", 200),
        (None, False, "stale", None),
    ],
)
def test_health_stale_is_http_200(
    client, monkeypatch, last_sample, expected_ok, expected_status, expected_age
):
    class Result:
        def fetchone(self):
            return (last_sample,)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _sql):
            return Result()

    store = SimpleNamespace(connect=lambda: Connection())
    monkeypatch.setattr(routes, "load_settings", lambda: object())
    monkeypatch.setattr(routes, "load_inventory", lambda: object())
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "current_sample_max_age_s", lambda: 120)
    monkeypatch.setattr(routes.time, "time", lambda: 1000)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": expected_ok,
        "status": expected_status,
        "last_sample_ts": last_sample,
        "last_sample_age_s": expected_age,
        "stale_after_s": 120,
    }
