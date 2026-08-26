"""聚合层测试：加权聚合必须等于对原始样本的直接平均；窗口选表正确。"""
from types import SimpleNamespace

import pytest

from gpumon.db.rollup import Rollup
from gpumon.db.store import Store, pick_table


@pytest.fixture(autouse=True)
def _active_inventory(monkeypatch):
    """Store 的 coverage 以 inventory 为准，测试拓扑也必须给出对应清单。"""
    inventory = SimpleNamespace(
        defaults=SimpleNamespace(gpu_count=8),
        clusters=[SimpleNamespace(
            key="cx",
            status="active",
            hosts=[SimpleNamespace(key="hx", status="active", gpu_count=2)],
        )],
    )
    monkeypatch.setattr("gpumon.db.store.load_inventory", lambda: inventory)
    monkeypatch.setattr(
        "gpumon.db.store.load_settings",
        lambda: SimpleNamespace(collector=SimpleNamespace(poll_interval_s=30)),
    )


def _setup(tmp_path):
    s = Store(path=tmp_path / "t.db")
    s.init_schema()
    conn = s.write_conn()
    with conn:
        conn.execute("INSERT INTO cluster(id,key,name,sort_order) VALUES(1,'cx','CX',1)")
        conn.execute("INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
                     "VALUES(1,1,'hx','a','HX',2)")
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(1,1,0,'U0')")
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(2,1,1,'U1')")
    return s


def _ins(s, gpu_id, ts, util):
    s.write_conn().execute(
        "INSERT OR REPLACE INTO sample_gpu(gpu_id,ts,util_gpu) VALUES(?,?,?)", (gpu_id, ts, util))


def test_pick_table():
    assert pick_table(12 * 3600)[0] == "rollup_gpu_5m"
    assert pick_table(24 * 3600)[0] == "rollup_gpu_5m"
    assert pick_table(48 * 3600)[0] == "rollup_gpu_1h"
    assert pick_table(7 * 24 * 3600)[0] == "rollup_gpu_1h"


def test_weighted_avg_equals_raw_avg(tmp_path):
    s = _setup(tmp_path)
    base = (1_700_000_000 // 300) * 300       # 对齐 5m 桶
    # 桶1 三个样本 10/20/30；桶2 两个样本 100/100。原始 5 样本均值=52
    for i, u in enumerate([10, 20, 30]):
        _ins(s, 1, base + i * 30, u)
    for i, u in enumerate([100, 100]):
        _ins(s, 1, base + 300 + i * 30, u)
    s.write_conn().commit()
    now = base + 3600                          # 推到整点桶封口之后，1h 聚合才会处理

    r = Rollup(s)
    r.roll_gpu_5m(now)
    r.roll_gpu_1h(now)

    # 5m 表（12h 窗）加权均值
    a12 = s.get_avg("12h", "gpu", "util_gpu", now=now)
    got = next(it for it in a12 if it["gpu_id"] == 1)
    assert round(got["avg"]) == 52
    assert round(got["max"]) == 100

    # 1h 表（72h 窗）加权均值，应与原始一致
    a72 = s.get_avg("72h", "gpu", "util_gpu", now=now)
    got72 = next(it for it in a72 if it["gpu_id"] == 1)
    assert round(got72["avg"]) == 52


def test_host_scope_weighted(tmp_path):
    s = _setup(tmp_path)
    base = (1_700_000_000 // 300) * 300
    # 卡1 一个桶 util=20（1 样本）；卡2 一个桶 util=80（3 样本）
    _ins(s, 1, base, 20)
    for i, u in enumerate([80, 80, 80]):
        _ins(s, 2, base + i * 30, u)
    s.write_conn().commit()
    now = base + 600
    Rollup(s).roll_gpu_5m(now)
    # host 加权 = (20*1 + 80*3) / 4 = 65
    items = s.get_avg("12h", "host", "util_gpu", now=now)
    assert round(items[0]["avg"]) == 65
    assert items[0]["n_gpus"] == 2


def test_series_has_points(tmp_path):
    s = _setup(tmp_path)
    base = (1_700_000_000 // 300) * 300
    for i, u in enumerate([10, 20, 30]):
        _ins(s, 1, base + i * 30, u)
    s.write_conn().commit()
    now = base + 600
    Rollup(s).roll_gpu_5m(now)
    pts = s.get_series("gpu", 1, "util_gpu", "12h", now=now)
    assert len(pts) == 1 and round(pts[0][1]) == 20


def test_coverage_uses_active_inventory_capacity(tmp_path, monkeypatch):
    s = _setup(tmp_path)
    conn = s.write_conn()
    with conn:
        conn.execute(
            "INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
            "VALUES(2,1,'planned','p','Planned',20)"
        )
        conn.execute(
            "INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
            "VALUES(3,1,'retired','r','Retired',20)"
        )
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(3,2,0,'UP')")
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(4,3,0,'UR')")

    inventory = SimpleNamespace(
        defaults=SimpleNamespace(gpu_count=8),
        clusters=[SimpleNamespace(
            key="cx",
            status="active",
            hosts=[
                SimpleNamespace(key="hx", status="active", gpu_count=4),
                SimpleNamespace(key="planned", status="planned", gpu_count=20),
                SimpleNamespace(key="retired", status="retired", gpu_count=20),
            ],
        )],
    )
    monkeypatch.setattr("gpumon.db.store.load_inventory", lambda: inventory)
    monkeypatch.setattr(
        "gpumon.db.store.load_settings",
        lambda: SimpleNamespace(collector=SimpleNamespace(poll_interval_s=3600)),
    )

    now = 1_700_000_000
    bucket = ((now - 300) // 300) * 300
    with conn:
        # active 主机只有 1 张卡有 12 个观测；清单预期 4 张，coverage 应为 1/4。
        conn.execute(
            "INSERT INTO rollup_gpu_5m(gpu_id,bucket_ts,n,util_gpu_avg,util_gpu_max) "
            "VALUES(1,?,12,20,20)", (bucket,)
        )
        # planned/retired 即使残留旧 rollup，也不能污染均值或 coverage。
        conn.execute(
            "INSERT INTO rollup_gpu_5m(gpu_id,bucket_ts,n,util_gpu_avg,util_gpu_max) "
            "VALUES(3,?,12,100,100)", (bucket,)
        )
        conn.execute(
            "INSERT INTO rollup_gpu_5m(gpu_id,bucket_ts,n,util_gpu_avg,util_gpu_max) "
            "VALUES(4,?,12,100,100)", (bucket,)
        )

    host = s.get_avg("12h", "host", "util_gpu", now=now)[0]
    cluster = s.get_avg("12h", "cluster", "util_gpu", now=now)[0]
    global_item = s.get_avg("12h", "global", "util_gpu", now=now)[0]
    gpu_items = s.get_avg("12h", "gpu", "util_gpu", now=now)

    for item in (host, cluster, global_item):
        assert item["avg"] == 20.0
        assert item["n_gpus"] == 4
        assert item["coverage"] == 0.25
    assert [item["gpu_id"] for item in gpu_items] == [1]
    assert gpu_items[0]["coverage"] == 1.0


@pytest.mark.parametrize(
    ("scope", "entity_id"),
    [("unknown", 1), ("gpu", None), ("host", 0), ("global", 1)],
)
def test_series_rejects_invalid_scope_id_combinations(tmp_path, scope, entity_id):
    s = _setup(tmp_path)
    with pytest.raises(ValueError):
        s.get_series(scope, entity_id, "util_gpu", "12h", now=1_700_000_000)
