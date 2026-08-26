"""退役过滤测试：status=retired 的主机/集群不下发给网页（DB 行仍在，历史保留）。"""
from types import SimpleNamespace

from gpumon.api.routes import _drop_retired, _retired_inventory_host_keys


def _topo():
    # 三个集群：alpha 正常双机；legacy-single 单机（将退役）；mixed 双机（退役其一）
    return [
        {"key": "alpha", "hosts": [{"key": "alpha-1"}, {"key": "alpha-2"}]},
        {"key": "legacy-single", "hosts": [{"key": "legacy-a100-1"}]},
        {"key": "mixed", "hosts": [{"key": "m-1"}, {"key": "m-2"}]},
    ]


def test_retired_host_dropped_and_empty_cluster_hidden():
    cluster_meta = {
        "alpha": {"status": "active"},
        "legacy-single": {"status": "retired"},
        "mixed": {"status": "active"},
    }
    host_meta = {
        "alpha-1": {"status": "active"}, "alpha-2": {"status": "active"},
        "legacy-a100-1": {"status": "retired"},
        "m-1": {"status": "retired"}, "m-2": {"status": "active"},
    }
    out = _drop_retired(_topo(), cluster_meta, host_meta)
    keys = {c["key"] for c in out}
    # 退役单机集群整簇消失
    assert "legacy-single" not in keys
    # 正常集群保留，且卡数不变
    assert next(c for c in out if c["key"] == "alpha")["hosts"] == [
        {"key": "alpha-1"}, {"key": "alpha-2"}]
    # 混合集群保留，只滤掉退役那台
    mixed = next(c for c in out if c["key"] == "mixed")
    assert [h["key"] for h in mixed["hosts"]] == ["m-2"]


def test_cluster_retired_hides_all_its_hosts():
    # 集群标 retired，即使主机没标，也整簇隐藏
    out = _drop_retired(
        [{"key": "legacy-single", "hosts": [{"key": "legacy-a100-1"}]}],
        {"legacy-single": {"status": "retired"}},
        {"legacy-a100-1": {"status": "active"}},
    )
    assert out == []


def test_missing_meta_defaults_to_visible():
    # meta 缺失（DB 有、inventory 无）不应被误删
    out = _drop_retired(
        [{"key": "ghost", "hosts": [{"key": "g-1"}]}], {}, {})
    assert len(out) == 1 and out[0]["key"] == "ghost"


def test_all_active_unchanged():
    cm = {"alpha": {"status": "active"}, "mixed": {"status": "active"}}
    hm = {"alpha-1": {"status": "active"}, "alpha-2": {"status": "active"},
          "m-1": {"status": "active"}, "m-2": {"status": "active"}}
    topo = [c for c in _topo() if c["key"] != "legacy-single"]
    out = _drop_retired(topo, cm, hm)
    assert out == topo


def test_retired_host_keys_inherit_cluster_retirement(monkeypatch):
    inventory = SimpleNamespace(clusters=[
        SimpleNamespace(
            status="retired",
            hosts=[SimpleNamespace(key="cluster-retired", status="active")],
        ),
        SimpleNamespace(
            status="active",
            hosts=[
                SimpleNamespace(key="host-retired", status="retired"),
                SimpleNamespace(key="planned", status="planned"),
                SimpleNamespace(key="active", status="active"),
            ],
        ),
    ])
    monkeypatch.setattr("gpumon.api.routes.load_inventory", lambda: inventory)

    assert _retired_inventory_host_keys() == {"cluster-retired", "host-retired"}
