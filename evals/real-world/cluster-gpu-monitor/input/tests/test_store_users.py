"""实时使用人和 GPU·小时查询的回归测试。"""

from types import SimpleNamespace

import pytest

from gpumon.db.store import Store


def _setup_store(tmp_path) -> Store:
    store = Store(path=tmp_path / "users.db")
    store.init_schema()
    conn = store.write_conn()
    with conn:
        conn.execute("INSERT INTO cluster(id,key,name,sort_order) VALUES(1,'cluster','Cluster',1)")
        conn.execute(
            "INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
            "VALUES(1,1,'host','host-alias','Host',2)"
        )
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(1,1,0,'GPU-1')")
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(2,1,1,'GPU-2')")
    return store


def _insert_gpu(store: Store, gpu_id: int, ts: int) -> None:
    store.write_conn().execute(
        "INSERT INTO sample_gpu(gpu_id,ts,util_gpu) VALUES(?,?,?)", (gpu_id, ts, 50)
    )


def _insert_proc(store: Store, gpu_id: int, ts: int, pid: int,
                 username: str, mem_used_mib: int | None) -> None:
    store.write_conn().execute(
        "INSERT INTO sample_proc(gpu_id,ts,pid,username,comm,mem_used_mib) "
        "VALUES(?,?,?,?,?,?)",
        (gpu_id, ts, pid, username, "python", mem_used_mib),
    )


def test_snapshot_uses_processes_from_latest_gpu_round(tmp_path):
    store = _setup_store(tmp_path)
    _insert_gpu(store, 1, 100)
    _insert_proc(store, 1, 100, 10, "old-user", 1024)
    _insert_gpu(store, 1, 200)
    store.write_conn().commit()

    snapshot = store.get_snapshot()

    assert snapshot["gpus"][1]["ts"] == 200
    assert 1 not in snapshot["procs"]


def test_users_current_ignores_stale_and_non_memory_processes(tmp_path):
    store = _setup_store(tmp_path)
    _insert_gpu(store, 1, 250)
    _insert_proc(store, 1, 250, 10, "alice", 1024)
    _insert_proc(store, 1, 250, 11, "zero-memory", 0)
    _insert_gpu(store, 2, 100)
    _insert_proc(store, 2, 100, 20, "stale-user", 2048)
    store.write_conn().commit()

    users = store.get_users_current(now=300, freshness_s=120)

    assert users == [{"username": "alice", "distinct_gpus": 1, "mem_gb": 1.0}]


def test_gpu_hours_deduplicates_same_user_gpu_and_round(tmp_path, monkeypatch):
    store = _setup_store(tmp_path)
    monkeypatch.setattr(
        "gpumon.db.store.load_settings",
        lambda: SimpleNamespace(collector=SimpleNamespace(poll_interval_s=3600)),
    )

    # alice 在 GPU-1 第一轮有两个 PID，也只能计一个 GPU·小时；第二轮再计一个。
    _insert_proc(store, 1, 100, 10, "alice", 100)
    _insert_proc(store, 1, 100, 11, "alice", 200)
    _insert_proc(store, 1, 200, 12, "alice", 300)
    # 没占显存的进程不计时。
    _insert_proc(store, 2, 100, 20, "alice", 0)
    # 不同用户共享同一轮仍分别计时；bob 还占了另一张卡。
    _insert_proc(store, 1, 100, 30, "bob", 400)
    _insert_proc(store, 2, 100, 31, "bob", 500)
    store.write_conn().commit()

    top_by_user = {
        item["username"]: item
        for item in store.get_users_top("24h", cluster_key="cluster", now=1000)
    }
    ranking_by_user = {
        item["username"]: item
        for item in store.get_users_ranking("24h", now=1000)["users"]
    }

    assert top_by_user["alice"]["gpu_hours"] == 2.0
    assert top_by_user["alice"]["distinct_gpus"] == 1
    assert top_by_user["bob"]["gpu_hours"] == 2.0
    assert top_by_user["bob"]["distinct_gpus"] == 2
    assert ranking_by_user["alice"]["total"] == 2.0
    assert ranking_by_user["alice"]["by_machine"] == {"host": 2.0}
    assert ranking_by_user["bob"]["total"] == 2.0


def test_user_queries_exclude_retired_hosts_before_aggregation(tmp_path, monkeypatch):
    store = _setup_store(tmp_path)
    monkeypatch.setattr(
        "gpumon.db.store.load_settings",
        lambda: SimpleNamespace(collector=SimpleNamespace(poll_interval_s=3600)),
    )
    conn = store.write_conn()
    with conn:
        conn.execute(
            "INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
            "VALUES(2,1,'retired','retired-alias','Retired',1)"
        )
        conn.execute("INSERT INTO gpu_card(id,host_id,gpu_index,uuid) VALUES(3,2,0,'GPU-3')")
    _insert_proc(store, 1, 100, 10, "alice", 100)
    _insert_proc(store, 3, 100, 20, "alice", 100)
    _insert_proc(store, 3, 100, 21, "retired-only", 100)
    conn.commit()

    top = {
        item["username"]: item
        for item in store.get_users_top(
            "24h", now=1000, excluded_host_keys={"retired"}
        )
    }
    ranking = store.get_users_ranking(
        "24h", now=1000, excluded_host_keys={"retired"}
    )

    assert top["alice"]["gpu_hours"] == 1.0
    assert "retired-only" not in top
    assert ranking["machines"] == [
        {"key": "host", "name": "Host", "cluster_key": "cluster"}
    ]
    assert ranking["users"] == [
        {"username": "alice", "total": 1.0, "by_machine": {"host": 1.0}}
    ]


def test_users_ranking_limits_complete_users_and_reports_truncation(tmp_path, monkeypatch):
    store = _setup_store(tmp_path)
    monkeypatch.setattr(
        "gpumon.db.store.load_settings",
        lambda: SimpleNamespace(collector=SimpleNamespace(poll_interval_s=3600)),
    )
    _insert_proc(store, 1, 100, 10, "alice", 100)
    _insert_proc(store, 1, 200, 11, "alice", 100)
    _insert_proc(store, 1, 100, 20, "bob", 100)
    _insert_proc(store, 1, 100, 30, "charlie", 100)
    store.write_conn().commit()

    ranking = store.get_users_ranking("24h", now=1000, limit=2)

    assert [user["username"] for user in ranking["users"]] == ["alice", "bob"]
    assert ranking["users"][0]["by_machine"] == {"host": 2.0}
    assert ranking["total_users"] == 3
    assert ranking["returned_users"] == 2
    assert ranking["truncated"] is True
    assert ranking["limit"] == 2


@pytest.mark.parametrize(
    ("method", "args", "kwargs"),
    [
        ("get_users_top", ("bad",), {}),
        ("get_users_top", ("24h",), {"by": "not-a-sort"}),
        ("get_users_top", ("24h",), {"limit": 0}),
        ("get_users_ranking", ("bad",), {}),
        ("get_users_ranking", ("24h",), {"limit": 0}),
    ],
)
def test_user_store_queries_reject_invalid_parameters(tmp_path, method, args, kwargs):
    store = _setup_store(tmp_path)
    with pytest.raises(ValueError):
        getattr(store, method)(*args, **kwargs)
