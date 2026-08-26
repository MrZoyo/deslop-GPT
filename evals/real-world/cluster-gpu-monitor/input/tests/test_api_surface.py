"""公开 API 字段、短缓存和生产文档开关。"""
from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from gpumon.api import routes
from gpumon.api.app import app, create_app
from gpumon.models import BadgeCfg, CapacityGroupCfg, ClusterCfg, HostCfg, Inventory


def test_public_topology_drops_collection_only_identifiers_and_unknown_fields():
    topology = [{
        "id": 1,
        "key": "cluster",
        "name": "Cluster",
        "sort_order": 0,
        "note": "集群备注",
        "note_i18n": {"zh": "集群备注", "en": "Cluster note"},
        "secret": "cluster-secret",
        "hosts": [{
            "id": 2,
            "cluster_id": 1,
            "key": "host",
            "ssh_alias": "private-jump-alias",
            "display_name": "Host",
            "gpu_count": 1,
            "note": "主机备注",
            "note_i18n": {"zh": "主机备注", "en": "Host note"},
            "secret": "host-secret",
            "gpus": [{
                "id": 3,
                "host_id": 2,
                "gpu_index": 0,
                "uuid": "GPU-private-hardware-id",
                "name": "GPU",
                "mem_total_mib": 80_000,
                "secret": "gpu-secret",
            }],
        }],
    }]

    public = routes._public_topology(topology)

    assert public[0]["key"] == "cluster"
    assert public[0]["note_i18n"] == {"zh": "集群备注", "en": "Cluster note"}
    assert "secret" not in public[0]
    host = public[0]["hosts"][0]
    assert host["note_i18n"] == {"zh": "主机备注", "en": "Host note"}
    assert "ssh_alias" not in host
    assert "secret" not in host
    gpu = host["gpus"][0]
    assert "uuid" not in gpu
    assert "secret" not in gpu


def test_inventory_ui_metadata_keeps_legacy_strings_and_i18n_maps(monkeypatch):
    inv = Inventory(
        badge_library=[BadgeCfg(
            key="self-built",
            text={"zh": "自建", "en": "Self-built"},
            tooltip={"en": "Built here"},
        )],
        capacity_groups=[CapacityGroupCfg(
            key="own",
            name="Own",
            description={"zh": "自建机房", "en": "On-prem"},
            badges=["self-built"],
        )],
        clusters=[ClusterCfg(
            key="c1",
            name="C1",
            capacity_group="own",
            note={"en": "Cluster note", "zh": "集群备注"},
            badges=["self-built"],
            hosts=[HostCfg(
                key="h1",
                ssh_alias="h1",
                display_name="H1",
                note={"fr": "Note d'hôte"},
            )],
        )],
    )
    monkeypatch.setattr(routes, "load_inventory", lambda: inv)

    groups, clusters, hosts = routes._inventory_ui_meta()

    assert groups[0]["description"] == "自建机房"
    assert groups[0]["description_i18n"] == {"zh": "自建机房", "en": "On-prem"}
    badge = groups[0]["badges"][0]
    assert badge["text"] == "自建"
    assert badge["text_i18n"] == {"zh": "自建", "en": "Self-built"}
    assert badge["tooltip"] == "Built here"
    assert badge["tooltip_i18n"] == {"en": "Built here"}
    assert clusters["c1"]["note"] == "Cluster note"
    assert clusters["c1"]["note_i18n"] == {"en": "Cluster note", "zh": "集群备注"}
    assert hosts["h1"]["note"] == "Note d'hôte"
    assert hosts["h1"]["note_i18n"] == {"fr": "Note d'hôte"}


def test_mutable_static_assets_require_browser_revalidation():
    client = TestClient(create_app())

    for path in ("/", "/index.html", "/js/components.js", "/css/style.css"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"


def test_snapshot_and_interactive_docs_are_disabled_by_default():
    client = TestClient(app)

    for path in ("/api/snapshot", "/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_interactive_docs_can_be_enabled_explicitly_for_development():
    client = TestClient(create_app(enable_docs=True))

    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_statistics_cache_reuses_only_the_current_bounded_bucket(monkeypatch):
    class FakeStore:
        def __init__(self):
            self.calls = []

        def get_avg(self, window, scope, metric, now=None):
            self.calls.append(now)
            return [{"avg": now}]

    store = FakeStore()
    monkeypatch.setattr(
        routes,
        "load_settings",
        lambda: SimpleNamespace(web=SimpleNamespace(stats_cache_ttl_s=15)),
    )
    routes._clear_stats_caches_for_tests()
    try:
        first = routes._get_avg(store, "24h", "gpu", "util_gpu", now=100)
        second = routes._get_avg(store, "24h", "gpu", "util_gpu", now=104)
        third = routes._get_avg(store, "24h", "gpu", "util_gpu", now=105)
    finally:
        routes._clear_stats_caches_for_tests()

    assert first == second
    assert third != second
    assert store.calls == [90, 105]
