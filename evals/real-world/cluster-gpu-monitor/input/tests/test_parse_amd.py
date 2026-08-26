"""AMD 解析单测。

⚠️ 样本按 AMD 官方文档的 amd-smi / rocm-smi 输出格式构造，**未在真机验证**。
拿到真实 AMD 机器后请用 scripts/probe_one.sh 抓一份实际输出，替换这里的样本。

覆盖重点是"容错"而非"字段齐全"：字段名换了、值带单位、值是 N/A、
显存单位是字节还是 MB、进程拿不到卡归属……这些是跨 ROCm 版本真正会踩的坑。
"""
from __future__ import annotations

import json

from gpumon.collector.parse import parse_probe
from gpumon.collector.parse_amd import (
    amd_uuid,
    parse_amdsmi,
    parse_rocmsmi,
)

# ---------------------------------------------------------------------------
# amd-smi（ROCm 6+）样本
# ---------------------------------------------------------------------------
AMDSMI_STATIC = [
    {"gpu": 0, "asic": {"market_name": "Instinct MI300X", "vendor_id": "0x1002"},
     "bus": {"bdf": "0000:01:00.0"},
     "board": {"product_serial": "PCB0123456"},
     "uuid": "7eff74a0-0000-1000-808f-7e20764e2714",
     "vram": {"size": {"value": 196592, "unit": "MB"}}},
    {"gpu": 1, "asic": {"market_name": "Instinct MI300X"},
     "bus": {"bdf": "0001:01:00.0"},
     "uuid": "b6ff74a0-0000-1000-80ae-7c8cefe1f084",
     "vram": {"size": {"value": 196592, "unit": "MB"}}},
]

AMDSMI_METRIC = [
    {"gpu": 0,
     "usage": {"gfx_activity": {"value": 87, "unit": "%"},
               "umc_activity": {"value": 41, "unit": "%"}},
     "mem_usage": {"used_vram": {"value": 121344, "unit": "MB"},
                   "total_vram": {"value": 196592, "unit": "MB"}},
     "temperature": {"hotspot": {"value": 71, "unit": "C"},
                     "edge": {"value": 52, "unit": "C"}},
     "power": {"socket_power": {"value": 542, "unit": "W"}}},
    {"gpu": 1,
     "usage": {"gfx_activity": {"value": 0, "unit": "%"},
               "umc_activity": {"value": 0, "unit": "%"}},
     "mem_usage": {"used_vram": {"value": 68000, "unit": "MB"},
                   "total_vram": {"value": 196592, "unit": "MB"}},
     "temperature": {"hotspot": {"value": 38, "unit": "C"}},
     "power": {"socket_power": {"value": 141, "unit": "W"}}},
]

AMDSMI_PROCESS = [
    {"gpu": 0, "process_list": [
        {"process_info": {"name": "python3", "pid": 4242,
                          "mem_usage": {"value": 512, "unit": "MB"},
                          "vram_mem": {"value": 121000, "unit": "MB"}}},
    ]},
    {"gpu": 1, "process_list": [
        {"process_info": {"name": "python3", "pid": 5150,
                          "vram_mem": {"value": 68000, "unit": "MB"}}},
    ]},
]


def test_amdsmi_basic_fields():
    gpus, procs = parse_amdsmi("amd-1", AMDSMI_STATIC, AMDSMI_METRIC, AMDSMI_PROCESS)
    assert len(gpus) == 2
    g0 = gpus[0]
    assert g0.index == 0
    assert g0.vendor == "amd"
    assert g0.name == "Instinct MI300X"
    assert g0.util_gpu == 87
    assert g0.util_mem == 41
    assert g0.mem_used_mib == 121344
    assert g0.mem_total_mib == 196592
    assert g0.temp_c == 71                     # hotspot 优先于 edge
    assert g0.power_w == 542.0
    assert g0.uuid == "7eff74a0-0000-1000-808f-7e20764e2714"


def test_amdsmi_process_attribution():
    gpus, procs = parse_amdsmi("amd-1", AMDSMI_STATIC, AMDSMI_METRIC, AMDSMI_PROCESS)
    by_uuid = {g.uuid: g for g in gpus}
    assert len(procs) == 2
    assert {p.pid for p in procs} == {4242, 5150}
    # 每个进程挂在对应卡上
    p0 = next(p for p in procs if p.pid == 4242)
    assert p0.gpu_uuid == gpus[0].uuid
    assert p0.gpu_uuid in by_uuid
    assert p0.comm == "python3"
    assert p0.mem_used_mib == 121000
    # smi 不给用户名，须留 None 等 PSMAP 回填
    assert p0.username is None


def test_amdsmi_flat_field_names():
    """字段没有 usage/mem_usage 包装层（部分版本如此）时也要能解析。"""
    static = [{"gpu": 0, "market_name": "MI250X", "uuid": "abc-123"}]
    metric = [{"gpu": 0, "gfx_activity": 55, "used_vram": 4096, "total_vram": 65536,
               "hotspot": 60, "socket_power": 300}]
    gpus, _ = parse_amdsmi("h", static, metric, None)
    assert gpus[0].util_gpu == 55
    assert gpus[0].mem_used_mib == 4096
    assert gpus[0].temp_c == 60
    assert gpus[0].power_w == 300.0


def test_amdsmi_na_values_become_none():
    static = [{"gpu": 0, "market_name": "MI300X", "uuid": "u1"}]
    metric = [{"gpu": 0, "usage": {"gfx_activity": "N/A"},
               "mem_usage": {"used_vram": "N/A", "total_vram": {"value": 100, "unit": "MB"}},
               "temperature": {"hotspot": "N/A"},
               "power": {"socket_power": "N/A"}}]
    gpus, _ = parse_amdsmi("h", static, metric, None)
    g = gpus[0]
    assert g.util_gpu is None
    assert g.mem_used_mib is None
    assert g.temp_c is None
    assert g.power_w is None
    assert g.mem_total_mib == 100          # 有值的字段不受影响


def test_amdsmi_bytes_unit_normalized():
    """显存给字节时要换算成 MiB，不能原样落库（否则显存显示会大出百万倍）。"""
    static = [{"gpu": 0, "uuid": "u"}]
    metric = [{"gpu": 0, "used_vram": {"value": 68702699520, "unit": "B"}}]
    gpus, _ = parse_amdsmi("h", static, metric, None)
    assert gpus[0].mem_used_mib == 65520


def test_amdsmi_bare_huge_number_guessed_as_bytes():
    """没有 unit 的裸大数按字节处理——>4GiB 的"MB"在物理上不成立。"""
    gpus, _ = parse_amdsmi("h", [{"gpu": 0, "uuid": "u"}],
                           [{"gpu": 0, "used_vram": 68702699520}], None)
    assert gpus[0].mem_used_mib == 65520


# ---------------------------------------------------------------------------
# UUID 兜底链：跨重启稳定性是历史数据不断裂的前提
# ---------------------------------------------------------------------------
def test_uuid_priority_uuid_first():
    e = {"uuid": "real-uuid-1", "board": {"product_serial": "S1"}, "bus": {"bdf": "0000:01:00.0"}}
    assert amd_uuid("h1", e, 0) == "real-uuid-1"


def test_uuid_falls_back_to_serial():
    e = {"board": {"product_serial": "PCB999"}, "bus": {"bdf": "0000:01:00.0"}}
    assert amd_uuid("h1", e, 0) == "AMD-PCB999"


def test_uuid_falls_back_to_pci_bdf():
    """没 uuid 没序列号时用 PCI 地址——它跨重启稳定，是可靠兜底。"""
    e = {"bus": {"bdf": "0000:63:00.0"}}
    assert amd_uuid("h1", e, 3) == "AMD-h1-0000:63:00.0"


def test_uuid_last_resort_index():
    assert amd_uuid("h1", {}, 5) == "AMD-h1-idx5"


def test_uuid_ignores_placeholder_zero():
    """uuid 为 0x0 / 0 是未实现的占位，不能当成真 uuid（否则多卡会撞 UNIQUE）。"""
    assert amd_uuid("h1", {"uuid": "0x0", "bus": {"bdf": "0000:01:00.0"}}, 0) == "AMD-h1-0000:01:00.0"


# ---------------------------------------------------------------------------
# rocm-smi 回退路径
# ---------------------------------------------------------------------------
ROCMSMI = {
    "card0": {
        "Device Name": "Instinct MI210",
        "Unique ID": "0x1a2b3c4d5e6f",
        "GPU use (%)": "93",
        "GPU Memory use (%)": "48",
        "VRAM Total Memory (B)": "68702699520",
        "VRAM Total Used Memory (B)": "34351349760",
        "Temperature (Sensor junction) (C)": "68.0",
        "Average Graphics Package Power (W)": "290.0",
    },
    "card1": {
        "Device Name": "Instinct MI210",
        "Unique ID": "0x9f8e7d6c5b4a",
        "GPU use (%)": "0",
        "GPU Memory use (%)": "0",
        "VRAM Total Memory (B)": "68702699520",
        "VRAM Total Used Memory (B)": "10737418240",
        "Temperature (Sensor junction) (C)": "35.0",
        "Average Graphics Package Power (W)": "42.0",
    },
}


def test_rocmsmi_basic():
    gpus, _ = parse_rocmsmi("amd-2", ROCMSMI, None)
    assert len(gpus) == 2
    g = gpus[0]
    assert g.index == 0
    assert g.vendor == "amd"
    assert g.name == "Instinct MI210"
    assert g.util_gpu == 93
    assert g.util_mem == 48
    assert g.mem_total_mib == 65520          # 字节 → MiB
    assert g.mem_used_mib == 32760
    assert g.temp_c == 68
    assert g.power_w == 290.0


def test_rocmsmi_card_order_is_numeric():
    """card10 不能排在 card2 前面——字典序会让卡号错位。"""
    data = {f"card{i}": {"GPU use (%)": str(i)} for i in (0, 1, 2, 10, 11)}
    gpus, _ = parse_rocmsmi("h", data, None)
    assert [g.index for g in gpus] == [0, 1, 2, 10, 11]


def test_rocmsmi_single_card_pid_attribution():
    """单卡机：--showpids 没给卡归属也能安全归到唯一那张卡。"""
    data = {"card0": {"GPU use (%)": "50", "Unique ID": "0xaa"}}
    pids = {"PID 1234": {"Process Name": "train.py", "VRAM Used": "1073741824"}}
    gpus, procs = parse_rocmsmi("h", data, pids)
    assert len(procs) == 1
    assert procs[0].pid == 1234
    assert procs[0].gpu_uuid == gpus[0].uuid
    assert procs[0].mem_used_mib == 1024


def test_rocmsmi_multicard_without_mapping_drops_procs():
    """多卡且拿不到 pid→GPU 映射时宁可不归属，避免统计失真。"""
    pids = {"PID 1234": {"Process Name": "train.py"}}
    gpus, procs = parse_rocmsmi("h", ROCMSMI, pids)
    assert len(gpus) == 2
    assert procs == []


def test_rocmsmi_multicard_with_pidgpus_mapping():
    pids = {"PID 777": {"Process Name": "train.py", "VRAM Used": "2147483648"}}
    lines = ["PID 777 is using 1 DRM device(s):", "PID 777 is using GPU 1"]
    gpus, procs = parse_rocmsmi("h", ROCMSMI, pids, lines)
    assert len(procs) == 1
    assert procs[0].gpu_uuid == gpus[1].uuid       # 归到 card1
    assert procs[0].mem_used_mib == 2048


# ---------------------------------------------------------------------------
# 端到端：走 parse_probe 的分段分派 + PSMAP 回填用户名
# ---------------------------------------------------------------------------
def _probe_text_amd() -> str:
    return "\n".join([
        "##META", "1700000000", "amdnode", "128",
        "##LOADAVG", "12.5 10.2 9.9 3/1234 5678",
        "##MEMINFO", "MemTotal:       2113929216 kB", "MemAvailable:   1056964608 kB",
        "##CPU1", "cpu  100 0 50 1000 10 0 0 0",
        "##CPU2", "cpu  200 0 100 1500 20 0 0 0",
        "##VENDOR", "amd",
        "##AMDSMI_STATIC", json.dumps(AMDSMI_STATIC),
        "##AMDSMI_METRIC", json.dumps(AMDSMI_METRIC),
        "##AMDSMI_PROCESS", json.dumps(AMDSMI_PROCESS),
        "##PSMAP", "4242 alice python3", "5150 verylongusername_bob python3",
        "##END",
    ])


def test_parse_probe_dispatches_to_amd_and_fills_usernames():
    r = parse_probe("amd-1", _probe_text_amd())
    assert r.ok
    assert r.vendor == "amd"
    assert r.remote_hostname == "amdnode"
    assert len(r.gpus) == 2
    assert all(g.vendor == "amd" for g in r.gpus)
    users = {p.pid: p.username for p in r.procs}
    assert users == {4242: "alice", 5150: "verylongusername_bob"}
    # 主机指标仍照常解析（与厂商无关）
    assert r.host.ncpu == 128
    assert r.host.load1 == 12.5
    assert r.host.cpu_util_pct is not None


def test_parse_probe_vendor_none_is_ok_with_zero_gpus():
    """没装任何 smi 的机器：算采集成功但零卡，不能报 ok=False（否则healthy 灯常红）。"""
    text = "\n".join([
        "##META", "1700000000", "cpubox", "8",
        "##LOADAVG", "0.1 0.1 0.1 1/1 1",
        "##MEMINFO", "MemTotal:       1048576 kB", "MemAvailable:    524288 kB",
        "##CPU1", "cpu  1 0 1 10 0 0 0 0",
        "##CPU2", "cpu  2 0 2 20 0 0 0 0",
        "##VENDOR", "none",
        "##PSMAP",
        "##END",
    ])
    r = parse_probe("cpu-1", text)
    assert r.ok
    assert r.vendor == "none"
    assert r.gpus == []
    assert r.procs == []


def test_parse_probe_without_vendor_section_defaults_nvidia():
    """向后兼容：老探测脚本没有 ##VENDOR 段时按 NVIDIA 解析。"""
    text = "\n".join([
        "##META", "1700000000", "oldnode", "64",
        "##LOADAVG", "1.0 1.0 1.0 1/1 1",
        "##MEMINFO", "MemTotal:       1048576 kB", "MemAvailable:    524288 kB",
        "##CPU1", "cpu  1 0 1 10 0 0 0 0",
        "##CPU2", "cpu  2 0 2 20 0 0 0 0",
        "##GPU", "0, GPU-abc, NVIDIA H100, 75, 30, 40960, 81559, 62, 350.5",
        "##APPS", "GPU-abc, 999, 40000",
        "##PSMAP", "999 carol python3",
        "##END",
    ])
    r = parse_probe("nv-1", text)
    assert r.ok
    assert r.vendor == "nvidia"
    assert len(r.gpus) == 1
    assert r.gpus[0].vendor == "nvidia"
    assert r.gpus[0].util_gpu == 75
    assert r.procs[0].username == "carol"
