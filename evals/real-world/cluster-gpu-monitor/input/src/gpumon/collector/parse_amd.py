"""AMD (ROCm) 探测输出解析。纯函数，无 IO，便于单测。

两条数据源，优先 amd-smi（ROCm 6+ 的新 CLI），回退 rocm-smi（老 ROCm）：
  amd-smi static/metric/process --json
  rocm-smi --show* --json

**为什么解析写得这么"松"**：amd-smi 的 JSON 字段名和嵌套层级跨 ROCm 小版本改过多次
（usage.gfx_activity vs gfx_activity、值有时是裸数字有时是 {"value":..,"unit":..}、
显存单位有 B/MB 两种）。这里不写死路径，而是"按 key 名在嵌套结构里找第一个命中"，
并统一做单位归一。宁可多试几个别名，也不要在客户的 ROCm 版本上直接解析失败。

⚠️ 本模块按 AMD 官方文档的输出格式实现，并用构造样本做了单测，
   但**尚未在真实 AMD 机器上验证过**。拿到真机后请用
   `scripts/probe_one.sh <alias>` core对一遍实际字段名。
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..models import MAX_GPUS_PER_HOST, MAX_PROCESSES_PER_HOST, GpuSample, ProcSample

_NA = {"", "n/a", "na", "none", "null", "[n/a]", "[not supported]", "unknown"}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def _load_json(lines: list[str]) -> Any:
    """把一段行还原成 JSON。前后可能夹杂告警行，故从第一个 { 或 [ 起截取。"""
    raw = "\n".join(lines).strip()
    if not raw:
        return None
    start = min((i for i in (raw.find("{"), raw.find("[")) if i >= 0), default=-1)
    if start < 0:
        return None
    try:
        return json.loads(raw[start:])
    except (ValueError, TypeError):
        return None


def _num(v: Any) -> float | None:
    """取数值。兼容三种形态：裸数字 / 字符串 / {"value": X, "unit": "Y"}。

    N/A 一类占位统一变 None —— 与 NVIDIA 侧 _to_int/_to_float 的语义保持一致。
    """
    if isinstance(v, dict):
        # {"value": 42, "unit": "%"}；有些版本用 "val"
        for k in ("value", "val"):
            if k in v:
                return _num(v[k])
        return None
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.lower() in _NA:
        return None
    # "42.0 C" / "550 W" / "68702699520 B" → 抓开头的数字
    m = re.match(r"^[-+]?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _unit_of(v: Any) -> str | None:
    if isinstance(v, dict):
        u = v.get("unit") or v.get("units")
        return str(u).strip().lower() if u else None
    return None


def _find(obj: Any, names: tuple[str, ...], _depth: int = 0) -> Any:
    """在嵌套 dict/list 里深度优先找第一个 key 命中 names 的值（大小写不敏感）。

    names 按优先级排列：先在当前层找完整的优先级序列，再往下钻。
    这样 "gfx_activity" 即使被包在 usage/ 或 metric/ 下也能取到，
    而不必为每个 ROCm 版本写一条路径。
    """
    if _depth > 6 or obj is None:
        return None
    if isinstance(obj, dict):
        lower = {str(k).lower(): k for k in obj}
        for n in names:
            if n in lower:
                return obj[lower[n]]
        for v in obj.values():
            got = _find(v, names, _depth + 1)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _find(v, names, _depth + 1)
            if got is not None:
                return got
    return None


# 裸数字判定为"字节"的下限：1 TiB 当作 MiB 讲不通（没有 1PB 显存的卡），
# 所以超过这个值的无单位数一律按字节换算。rocm-smi 的 --showmeminfo 就给裸字节。
_BYTES_GUESS_FLOOR = 1 << 20


def _find_num(obj: Any, names: tuple[str, ...]) -> Any:
    """找"能取出数值"的字段，跳过纯容器层。

    为什么不能直接用 _find：amd-smi 把叶子包在同名容器里
    （`{"temperature": {"hotspot": {...}, "edge": {...}}}`）。
    _find 会先命中容器名 "temperature" 返回那个 dict，而它没有 value/val，
    于是 _num() 得到 None —— 温度、功耗会整列丢失。
    这里的规则：命中后必须能取出数值才算成功，否则钻进去继续按同一组名字找。
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        lower = {str(k).lower(): k for k in obj}
        for n in names:
            if n in lower:
                v = obj[lower[n]]
                if _num(v) is not None:
                    return v
                got = _find_num(v, names)       # 命中的是容器 → 继续下钻
                if got is not None:
                    return got
        for v in obj.values():
            got = _find_num(v, names)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = _find_num(v, names)
            if got is not None:
                return got
    return None


def _to_mib(v: Any) -> int | None:
    """显存归一到 MiB。amd-smi 常给 MB，rocm-smi 的 --showmeminfo 给字节。

    判断依据：显式 unit 优先；没有 unit 时按量级猜（见 _BYTES_GUESS_FLOOR）。
    """
    n = _num(v)
    if n is None:
        return None
    unit = _unit_of(v)
    if unit:
        if unit.startswith("b") and "mb" not in unit and "gb" not in unit:
            return int(n / (1024 * 1024))
        if unit.startswith("gb") or unit.startswith("gib"):
            return int(n * 1024)
        if unit.startswith("kb") or unit.startswith("kib"):
            return int(n / 1024)
        return int(n)          # mb / mib
    return int(n / (1024 * 1024)) if n > _BYTES_GUESS_FLOOR else int(n)


# ---------------------------------------------------------------------------
# UUID：跨重启必须稳定，否则历史会断
# ---------------------------------------------------------------------------
def amd_uuid(host_key: str, entry: Any, index: int) -> str:
    """AMD 卡的稳定标识，优先级：uuid → 序列号 → PCI(BDF) → index 兜底。

    为什么这条链很重要：DB 的 gpu_card.uuid 是 UNIQUE，历史采样全挂在它上面。
    NVIDIA 的 GPU-xxxx 天生跨重启稳定；AMD 的 rocm-smi 不保证给 uuid，
    所以退到"序列号"和"PCI 地址"——两者都不随重启变化。
    最后才用 index 兜底（重排卡序会导致历史错位，但至少不会崩）。
    """
    u = _find(entry, ("uuid", "gpu_uuid", "unique id", "unique_id"))
    s = None if u is None else str(_num(u) if isinstance(u, dict) else u).strip()
    if s and s.lower() not in _NA and s not in {"0x0", "0"}:
        return s if s.startswith("AMD-") or "-" in s else f"AMD-{s}"

    serial = _find(entry, ("product_serial", "serial_number", "asic_serial", "serial"))
    if serial is not None:
        ss = str(serial).strip()
        if ss and ss.lower() not in _NA:
            return f"AMD-{ss}"

    bdf = _find(entry, ("bdf", "pci_bus", "pci_bus_id", "bus_id"))
    if bdf is not None:
        bs = str(bdf).strip()
        if bs and bs.lower() not in _NA:
            return f"AMD-{host_key}-{bs}"

    return f"AMD-{host_key}-idx{index}"


# ---------------------------------------------------------------------------
# amd-smi 路径
# ---------------------------------------------------------------------------
def _gpu_index(entry: Any, fallback: int) -> int:
    for key in ("gpu", "gpu_id", "card", "device_id", "index"):
        v = _find(entry, (key,))
        n = _num(v)
        if n is not None:
            return int(n)
    return fallback


def parse_amdsmi(host_key: str, static: Any, metric: Any, process: Any) -> tuple[list[GpuSample], list[ProcSample]]:
    """解析 amd-smi 的 static/metric/process 三段 JSON。"""
    gpus: list[GpuSample] = []
    st_list = static if isinstance(static, list) else ([static] if static else [])
    me_list = metric if isinstance(metric, list) else ([metric] if metric else [])
    if len(st_list) > MAX_GPUS_PER_HOST or len(me_list) > MAX_GPUS_PER_HOST:
        raise ValueError("AMD GPU 数超过单机上限")

    # 以 metric 为主表（每卡一条），static 按 gpu index 对齐补型号/uuid
    st_by_idx = {_gpu_index(e, i): e for i, e in enumerate(st_list)}
    source = me_list or st_list
    for i, entry in enumerate(source):
        idx = _gpu_index(entry, i)
        st = st_by_idx.get(idx, {})
        merged = {"_metric": entry, "_static": st}

        name = _find(st, ("market_name", "product_name", "device_name", "name")) \
            or _find(entry, ("market_name", "product_name", "device_name"))
        util_gpu = _num(_find_num(entry, ("gfx_activity", "gfx_usage", "gpu_activity",
                                         "gpu_use (%)", "graphics_activity")))
        util_mem = _num(_find_num(entry, ("umc_activity", "memory_activity", "mem_activity",
                                         "umc_usage")))
        used = _find_num(entry, ("used_vram", "vram_used", "used_memory", "vram_used_memory"))
        total = _find_num(entry, ("total_vram", "vram_total", "total_memory")) \
            or _find_num(st, ("total_vram", "vram_total", "vram_size", "size", "total_memory"))
        # hotspot/junction 是同一个传感器的两种叫法，优先于 edge（edge 偏低、不反映实际热点）
        temp = _find_num(entry, ("hotspot", "junction", "edge", "gpu_temp", "temperature"))
        power = _find_num(entry, ("socket_power", "average_socket_power", "gpu_power",
                                  "current_socket_power", "power"))

        gpus.append(GpuSample(
            index=idx,
            uuid=amd_uuid(host_key, merged, idx),
            name=str(name).strip() if name else None,
            vendor="amd",
            util_gpu=None if util_gpu is None else int(round(util_gpu)),
            util_mem=None if util_mem is None else int(round(util_mem)),
            mem_used_mib=_to_mib(used),
            mem_total_mib=_to_mib(total),
            temp_c=None if _num(temp) is None else int(round(_num(temp))),
            power_w=_num(power),
        ))

    procs = _parse_amdsmi_process(process, gpus)
    return gpus, procs


def _parse_amdsmi_process(process: Any, gpus: list[GpuSample]) -> list[ProcSample]:
    """amd-smi process --json → ProcSample。进程挂到对应卡的 uuid 上。"""
    out: list[ProcSample] = []
    if not process:
        return out
    entries = process if isinstance(process, list) else [process]
    if len(entries) > MAX_GPUS_PER_HOST:
        raise ValueError("AMD 进程分组数超过单机 GPU 上限")
    uuid_by_idx = {g.index: g.uuid for g in gpus}
    for i, entry in enumerate(entries):
        idx = _gpu_index(entry, i)
        uuid = uuid_by_idx.get(idx)
        if uuid is None:
            continue
        plist = _find(entry, ("process_list", "processes", "process_info"))
        if plist is None:
            continue
        if isinstance(plist, dict):
            plist = [plist]
        if not isinstance(plist, list):
            continue
        for p in plist:
            if len(out) >= MAX_PROCESSES_PER_HOST:
                raise ValueError("AMD GPU 进程数超过单机上限")
            # 有的版本再包一层 {"process_info": {...}}
            info = p.get("process_info") if isinstance(p, dict) and "process_info" in p else p
            pid = _num(_find(info, ("pid", "process_id")))
            if pid is None:
                continue
            mem = _find(info, ("vram_mem", "vram_usage", "memory_usage", "mem_usage", "vram"))
            name = _find(info, ("name", "process_name", "comm"))
            out.append(ProcSample(
                gpu_uuid=uuid, pid=int(pid),
                username=None,                      # 由 PSMAP 段回填
                comm=str(name).strip() if name else None,
                mem_used_mib=_to_mib(mem),
            ))
    return out


# ---------------------------------------------------------------------------
# rocm-smi 回退路径
# ---------------------------------------------------------------------------
def parse_rocmsmi(host_key: str, data: Any, pids: Any,
                  pidgpus_lines: list[str] | None = None) -> tuple[list[GpuSample], list[ProcSample]]:
    """解析 rocm-smi --json。顶层形如 {"card0": {...}, "card1": {...}}。"""
    gpus: list[GpuSample] = []
    if not isinstance(data, dict):
        return gpus, []

    def card_no(k: str) -> int:
        m = re.search(r"(\d+)", k)
        return int(m.group(1)) if m else 0

    card_keys = sorted(
        (k for k in data if str(k).lower().startswith("card")), key=card_no
    )
    if len(card_keys) > MAX_GPUS_PER_HOST:
        raise ValueError("ROCm GPU 数超过单机上限")
    for key in card_keys:
        entry = data[key]
        if not isinstance(entry, dict):
            continue
        idx = card_no(str(key))
        # rocm-smi 的 key 是带单位的长英文名，故这里的别名列表要写全
        util_gpu = _num(_find_num(entry, ("gpu use (%)", "gpu_use", "gpu use")))
        util_mem = _num(_find_num(entry, ("gpu memory use (%)", "gpu_memory_use",
                                         "memory use (%)")))
        used = _find_num(entry, ("vram total used memory (b)", "vram_total_used_memory",
                                 "used memory (b)"))
        total = _find_num(entry, ("vram total memory (b)", "vram_total_memory"))
        temp = _find_num(entry, ("temperature (sensor junction) (c)",
                                 "temperature (sensor edge) (c)",
                                 "temperature (sensor memory) (c)"))
        power = _find_num(entry, ("average graphics package power (w)",
                                  "current socket graphics package power (w)",
                                  "average socket power (w)"))
        name = _find(entry, ("device name", "card series", "card model", "market name"))

        gpus.append(GpuSample(
            index=idx,
            uuid=amd_uuid(host_key, entry, idx),
            name=str(name).strip() if name else None,
            vendor="amd",
            util_gpu=None if util_gpu is None else int(round(util_gpu)),
            util_mem=None if util_mem is None else int(round(util_mem)),
            mem_used_mib=_to_mib(used),
            mem_total_mib=_to_mib(total),
            temp_c=None if _num(temp) is None else int(round(_num(temp))),
            power_w=_num(power),
        ))

    procs = _parse_rocmsmi_pids(pids, pidgpus_lines, gpus)
    return gpus, procs


def _parse_rocmsmi_pids(pids: Any, pidgpus_lines: list[str] | None,
                        gpus: list[GpuSample]) -> list[ProcSample]:
    """rocm-smi --showpids / --showpidgpus → ProcSample。

    痛点：老 rocm-smi 的 --showpids 只给"哪些 pid 在用 GPU"，不给 pid→哪张卡。
    有 --showpidgpus 时才能建映射；拿不到映射时，**只有单卡机器**能安全归属
    （只有一张卡，进程必然在它上面）；多卡且无映射则放弃归属，宁缺勿错——
    错误归属会让"使用人"和 GPU·小时统计整体失真。
    """
    out: list[ProcSample] = []
    if not gpus:
        return out
    uuid_by_idx = {g.index: g.uuid for g in gpus}

    # pid → [gpu index]，来自 --showpidgpus 的自由文本
    pid2gpus: dict[int, list[int]] = {}
    for ln in (pidgpus_lines or []):
        m = re.search(r"PID\s+(\d+)\s+is\s+using\s+.*?GPU", ln, re.I)
        if not m:
            continue
        pid = int(m.group(1))
        idxs = [int(x) for x in re.findall(r"\b(\d+)\b", ln[m.end():])]
        if idxs:
            pid2gpus[pid] = idxs
            if len(pid2gpus) > MAX_PROCESSES_PER_HOST:
                raise ValueError("ROCm PID 映射数超过单机上限")

    # 收集 pid 与其显存占用
    collected: dict[int, tuple[str | None, Any]] = {}
    if isinstance(pids, dict):
        for k, v in pids.items():
            m = re.search(r"(\d+)", str(k))
            if m and str(k).lower().startswith("pid"):
                pid = int(m.group(1))
                name = _find(v, ("process name", "name")) if isinstance(v, dict) else None
                mem = _find(v, ("vram used", "memory used", "vram_used")) if isinstance(v, dict) else None
                collected[pid] = (str(name).strip() if name else None, mem)
            elif isinstance(v, dict):
                p = _num(_find(v, ("pid",)))
                if p is not None:
                    collected[int(p)] = (
                        (lambda n: str(n).strip() if n else None)(_find(v, ("process name", "name"))),
                        _find(v, ("vram used", "memory used", "vram_used")),
                    )
            if len(collected) > MAX_PROCESSES_PER_HOST:
                raise ValueError("ROCm GPU 进程数超过单机上限")

    single = gpus[0].uuid if len(gpus) == 1 else None
    for pid, (comm, mem) in collected.items():
        targets = pid2gpus.get(pid)
        if targets:
            for gi in targets:
                uuid = uuid_by_idx.get(gi)
                if uuid:
                    if len(out) >= MAX_PROCESSES_PER_HOST:
                        raise ValueError("ROCm GPU 进程数超过单机上限")
                    out.append(ProcSample(gpu_uuid=uuid, pid=pid, username=None,
                                          comm=comm, mem_used_mib=_to_mib(mem)))
        elif single:
            if len(out) >= MAX_PROCESSES_PER_HOST:
                raise ValueError("ROCm GPU 进程数超过单机上限")
            out.append(ProcSample(gpu_uuid=single, pid=pid, username=None,
                                  comm=comm, mem_used_mib=_to_mib(mem)))
        # 多卡且无映射 → 跳过，见 docstring
    return out


def parse_amd_sections(host_key: str, sec: dict[str, list[str]]) -> tuple[list[GpuSample], list[ProcSample]]:
    """从 remote_probe 的分段里解析 AMD 数据。amd-smi 优先，无结果再试 rocm-smi。"""
    static = _load_json(sec.get("AMDSMI_STATIC", []))
    metric = _load_json(sec.get("AMDSMI_METRIC", []))
    process = _load_json(sec.get("AMDSMI_PROCESS", []))
    if static or metric:
        gpus, procs = parse_amdsmi(host_key, static, metric, process)
        if gpus:
            return gpus, procs

    data = _load_json(sec.get("ROCMSMI_JSON", []))
    pids = _load_json(sec.get("ROCMSMI_PIDS", []))
    return parse_rocmsmi(host_key, data, pids, sec.get("ROCMSMI_PIDGPUS", []))
