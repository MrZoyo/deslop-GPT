"""解析 remote_probe.sh 的输出为 ProbeResult。纯函数，无 IO，便于单测。

鲁棒原则：按 ##段 切分，逐段独立解析，单段异常不影响其它段；
所有数值缺失/[N/A]/[Not Supported] 一律变 None。
"""
from __future__ import annotations

from pydantic import ValidationError

from ..models import (
    MAX_GPUS_PER_HOST,
    MAX_PROCESSES_PER_HOST,
    GpuSample,
    HostSample,
    ProbeResult,
    ProcSample,
)
from .parse_amd import parse_amd_sections

_NA = {"", "[n/a]", "[not supported]", "[unknown error]", "n/a", "na"}
MAX_PROBE_LINES = 50_000
MAX_PROBE_TEXT_CHARS = 64 * 1024 * 1024


class ProbeDataError(ValueError):
    """远端探测结果违反结构/数量边界；消息只描述规则，不包含远端原值。"""


def _to_int(s: str | None):
    if s is None:
        return None
    s = s.strip()
    if s.lower() in _NA:
        return None
    try:
        return int(float(s))
    except (ValueError, OverflowError):
        return None


def _to_float(s: str | None):
    if s is None:
        return None
    s = s.strip()
    if s.lower() in _NA:
        return None
    try:
        return float(s)
    except (ValueError, OverflowError):
        return None


def _split_sections(raw: str) -> dict[str, list[str]]:
    if len(raw) > MAX_PROBE_TEXT_CHARS:
        raise ProbeDataError("输出文本超过解析上限")
    if raw.count("\n") + 1 > MAX_PROBE_LINES:
        raise ProbeDataError("输出行数超过解析上限")
    sections: dict[str, list[str]] = {}
    cur: str | None = None
    for line in raw.splitlines():
        if line.startswith("##"):
            cur = line[2:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
    return sections


def _cpu_util(cpu1: str, cpu2: str) -> float | None:
    """两次 /proc/stat 的 'cpu ' 行差分，算这段时间的 CPU 利用率(%)。"""
    try:
        a = [int(x) for x in cpu1.split()[1:]]
        b = [int(x) for x in cpu2.split()[1:]]
    except (ValueError, IndexError):
        return None
    if len(a) < 5 or len(b) < 5:
        return None
    # 字段: user nice system idle iowait irq softirq steal ...
    idle_a, idle_b = a[3] + a[4], b[3] + b[4]   # idle + iowait
    tot_a, tot_b = sum(a), sum(b)
    dtot, didle = tot_b - tot_a, idle_b - idle_a
    if dtot <= 0:
        return None
    return round(100.0 * (1.0 - didle / dtot), 1)


def _psmap(sec: dict[str, list[str]]) -> dict[int, tuple[str | None, str | None]]:
    """PSMAP 段 "pid user comm" → {pid: (user, comm)}。两条厂商路径共用。"""
    pid_map: dict[int, tuple[str | None, str | None]] = {}
    for line in sec.get("PSMAP", []):
        if len(pid_map) >= MAX_PROCESSES_PER_HOST:
            raise ProbeDataError("PSMAP 进程数超过单机上限")
        parts = line.split(None, 2)
        if len(parts) >= 2:
            pid = _to_int(parts[0])
            if pid is not None:
                pid_map[pid] = (parts[1], parts[2] if len(parts) >= 3 else None)
    return pid_map


def _fill_usernames(procs: list[ProcSample],
                    pid_map: dict[int, tuple[str | None, str | None]]) -> None:
    """按 pid 回填用户名。AMD 侧的 smi 不给用户名，一律靠 ps 的 PSMAP 段补。

    comm 只在 smi 没给出时才用 ps 的值 —— smi 的进程名通常更准（含完整可执行名）。
    """
    for p in procs:
        user, comm = pid_map.get(p.pid, (None, None))
        if p.username is None:
            p.username = user
        if not p.comm:
            p.comm = comm


def parse_probe(host_key: str, raw: str) -> ProbeResult:
    """解析一轮远端输出；不可信字段只会得到失败结果，不把校验异常抛给采集循环。"""
    try:
        return _parse_probe(host_key, raw)
    except ProbeDataError as exc:
        return ProbeResult(host_key=host_key, ok=False, error=str(exc))
    except (ValidationError, ValueError, TypeError, OverflowError, RecursionError):
        # Pydantic 错误会携带原始 input_value；这里故意不回显远端内容。
        return ProbeResult(host_key=host_key, ok=False, error="远端输出字段无效或超出允许范围")


def _parse_probe(host_key: str, raw: str) -> ProbeResult:
    sec = _split_sections(raw)
    if "END" not in sec:
        return ProbeResult(host_key=host_key, ok=False,
                           error="输出被截断（未见 ##END）")

    # META
    remote_hostname = None
    meta = sec.get("META", [])
    if len(meta) >= 2:
        remote_hostname = meta[1].strip() or None

    # 系统指标
    host = HostSample()
    if meta and len(meta) >= 3:
        host.ncpu = _to_int(meta[2])
    load = sec.get("LOADAVG", [])
    if load:
        parts = load[0].split()
        if len(parts) >= 3:
            host.load1, host.load5, host.load15 = (_to_float(parts[0]),
                                                   _to_float(parts[1]), _to_float(parts[2]))
    for line in sec.get("MEMINFO", []):
        if line.startswith("MemTotal:"):
            kb = _to_int(line.split()[1]) if len(line.split()) >= 2 else None
            host.mem_total_mib = kb // 1024 if kb is not None else None
        elif line.startswith("MemAvailable:"):
            kb = _to_int(line.split()[1]) if len(line.split()) >= 2 else None
            host.mem_avail_mib = kb // 1024 if kb is not None else None
    if host.mem_total_mib is not None and host.mem_avail_mib is not None:
        host.mem_used_mib = host.mem_total_mib - host.mem_avail_mib
    cpu1 = sec.get("CPU1", [""])
    cpu2 = sec.get("CPU2", [""])
    if cpu1 and cpu2:
        host.cpu_util_pct = _cpu_util(cpu1[0], cpu2[0])

    # 厂商：远端 ##VENDOR 段给出。老版本探测脚本没有该段 → 按 nvidia 处理（向后兼容）。
    vendor_lines = sec.get("VENDOR", [])
    vendor = (vendor_lines[0].strip().lower() if vendor_lines else "") or "nvidia"

    # GPU + 进程：按厂商分派。AMD 走 parse_amd（JSON），NVIDIA 走下面的 CSV。
    if vendor == "amd":
        gpus, procs = parse_amd_sections(host_key, sec)
        _fill_usernames(procs, _psmap(sec))
        return ProbeResult(host_key=host_key, ok=True, vendor=vendor,
                           remote_hostname=remote_hostname,
                           gpus=gpus, procs=procs, host=host)
    if vendor == "none":
        # 机器上没有可用的 GPU 工具：不是采集失败，就是没卡。ok=True 但零卡。
        return ProbeResult(host_key=host_key, ok=True, vendor=vendor,
                           remote_hostname=remote_hostname,
                           gpus=[], procs=[], host=host)

    # GPU（NVIDIA CSV）
    gpus: list[GpuSample] = []
    for line in sec.get("GPU", []):
        if not line.strip():
            continue
        if len(gpus) >= MAX_GPUS_PER_HOST:
            raise ProbeDataError("GPU 数超过单机上限")
        f = [x.strip() for x in line.split(",")]
        if len(f) < 9:
            continue
        index = _to_int(f[0])
        if index is None:
            raise ProbeDataError("GPU index 缺失或无效")
        gpus.append(GpuSample(
            index=index, uuid=f[1], name=f[2] or None, vendor="nvidia",
            util_gpu=_to_int(f[3]), util_mem=_to_int(f[4]),
            mem_used_mib=_to_int(f[5]), mem_total_mib=_to_int(f[6]),
            temp_c=_to_int(f[7]), power_w=_to_float(f[8]),
        ))

    pid_map = _psmap(sec)

    # APPS: gpu_uuid, pid, used_memory
    procs: list[ProcSample] = []
    for line in sec.get("APPS", []):
        if not line.strip():
            continue
        if len(procs) >= MAX_PROCESSES_PER_HOST:
            raise ProbeDataError("GPU 进程数超过单机上限")
        f = [x.strip() for x in line.split(",")]
        if len(f) < 3:
            continue
        pid = _to_int(f[1])
        if pid is None:
            continue
        user, comm = pid_map.get(pid, (None, None))
        procs.append(ProcSample(gpu_uuid=f[0], pid=pid, username=user, comm=comm,
                                mem_used_mib=_to_int(f[2])))

    return ProbeResult(host_key=host_key, ok=True, vendor=vendor,
                       remote_hostname=remote_hostname,
                       gpus=gpus, procs=procs, host=host)
