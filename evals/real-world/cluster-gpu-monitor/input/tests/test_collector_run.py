"""采集整轮对象预算与告警持久化的回归测试。"""
from __future__ import annotations

from gpumon.collector import run as run_module
from gpumon.collector.run import _RoundBudget, _summary
from gpumon.db.store import Store
from gpumon.models import GpuSample, ProbeResult, ProcSample


def _result(host: str, gpu_count: int, proc_count: int) -> ProbeResult:
    gpus = [
        GpuSample(index=i, uuid=f"GPU-{host}-{i}")
        for i in range(gpu_count)
    ]
    gpu_uuid = gpus[0].uuid if gpus else f"GPU-{host}-missing"
    procs = [
        ProcSample(gpu_uuid=gpu_uuid, pid=i + 1, username="user", comm="python")
        for i in range(proc_count)
    ]
    return ProbeResult(host_key=host, ok=True, gpus=gpus, procs=procs)


def test_round_process_budget_drops_only_overflowing_host_details(monkeypatch):
    monkeypatch.setattr(run_module, "MAX_PROCESSES_PER_ROUND", 2)
    monkeypatch.setattr(run_module, "MAX_GPUS_PER_ROUND", 10)
    budget = _RoundBudget()

    first = budget.apply(_result("first", 1, 2))
    overflow = budget.apply(_result("overflow", 1, 1))

    assert first.ok and len(first.procs) == 2
    assert overflow.ok and len(overflow.gpus) == 1 and overflow.procs == []
    assert "已省略本机进程明细" in (overflow.warning or "")
    assert budget.procs == 2


def test_round_gpu_budget_turns_overflow_into_controlled_failure(monkeypatch):
    monkeypatch.setattr(run_module, "MAX_GPUS_PER_ROUND", 1)
    budget = _RoundBudget()

    overflow = budget.apply(_result("overflow", 2, 0))

    assert not overflow.ok
    assert overflow.gpus == [] and overflow.procs == []
    assert "GPU 样本超过总上限" in (overflow.error or "")


def test_summary_surfaces_successful_result_warning():
    result = _result("warned", 1, 0)
    result.warning = "进程明细已省略"

    text = _summary(0, [result])

    assert "成功 1/1" in text
    assert "⚠ warned: 进程明细已省略" in text


def test_record_round_persists_and_clears_success_warning(tmp_path):
    store = Store(path=tmp_path / "warning.db")
    store.init_schema()
    conn = store.write_conn()
    with conn:
        conn.execute(
            "INSERT INTO cluster(id,key,name,sort_order) VALUES(1,'cluster','Cluster',1)"
        )
        conn.execute(
            "INSERT INTO host(id,cluster_id,key,ssh_alias,display_name,gpu_count) "
            "VALUES(1,1,'warned','alias','Warned',1)"
        )

    warned = ProbeResult(host_key="warned", ok=True, warning="进程明细已省略")
    store.record_round(100, [warned])
    row = conn.execute(
        "SELECT consec_fail,last_error FROM collector_status WHERE host_id=1"
    ).fetchone()
    assert tuple(row) == (0, "进程明细已省略")

    store.record_round(200, [ProbeResult(host_key="warned", ok=True)])
    row = conn.execute(
        "SELECT last_error FROM collector_status WHERE host_id=1"
    ).fetchone()
    assert row[0] is None
