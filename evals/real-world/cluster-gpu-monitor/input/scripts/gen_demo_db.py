#!/usr/bin/env python3
"""生成演示数据库 + 配套 inventory —— 没有任何真实机器也能把网页跑起来。

两个用途：
  1. 零硬件评估：把库填满，让总览/集群/主机/GPU/排行每一页都有东西可渲染；
  2. 大规模压测：真实部署只有几十张卡，`--scale large` 造 256 卡，用来看
     tooltip 长度、表格列溢出、堆叠条分隔这些只在大规模才暴露的边界。

三条别改坏的约束：
  - inventory 与 DB 出自同一份拓扑描述。网页是「DB 拓扑 + inventory 元数据」
    合并渲染的（见 api/routes.py 的 _topology_with_inventory_placeholders），
    两边 key 不一致会出现空集群 / 幽灵主机 / 卡片全是占位符。
  - 聚合表不自己算，调项目自己的 Rollup。1h 表是按 n 加权再聚合（不是对均值
    再平均），自己重写一份迟早和生产口径分叉。
  - 时间戳按真实采集周期 30s 对齐。get_util_recent 的 600s 窗、rollup 的
    300s/3600s 分桶、gpu_hours = 样本数 x interval 都建立在这个间隔上。

演示内容（算力域/集群/用户名等）全部来自 demo_fixtures.py，本文件只管造时序与写库。
用法见 --help；跑完会打印查看命令。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

# 允许直接 `python scripts/gen_demo_db.py`（不经安装）。append 而非 insert：
# 已安装的包优先，避免同名包被意外遮蔽。
_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(_ROOT / "src"))
sys.path.append(str(Path(__file__).resolve().parent))

import yaml  # noqa: E402  项目已依赖 pyyaml，不引入新依赖

import demo_fixtures as FX  # noqa: E402  演示内容（搞怪命名）都在这里
from demo_safety import (  # noqa: E402
    DEMO_INVENTORY_MARKER,
    DemoSafetyError,
    assert_safe_generation_target,
    demo_database_state,
    finalize_demo_database,
    initialize_demo_database_marker,
    is_demo_inventory,
)

TICK = 30              # 采集周期，须与 settings 的 collector.poll_interval_s 一致
FLUSH_ROWS = 100_000   # 攒够这么多行 executemany 一次，兼顾内存与吞吐


# ---------------------------------------------------------------------------
# 拓扑：把 fixtures 展开成"每张卡一条"的扁平列表
# ---------------------------------------------------------------------------
class Topology:
    """一份拓扑同时供 inventory YAML 与 DB 使用，保证两边 key 完全一致。"""

    def __init__(self, domains: list[dict], clusters: list[dict],
                 badge_library: list[dict] | None = None):
        self.domains = domains
        self.clusters = clusters
        self.badge_library = badge_library or []

    @property
    def active_clusters(self) -> list[dict]:
        """会产生采样的集群：planned 没接入、retired 已停采，都不造数据。

        注意 retired 仍要写进 inventory（否则网页会把它当"清单里已删"的孤儿），
        只是不产生新样本 —— 这正好还原真实退役场景。
        """
        return [c for c in self.clusters if c["status"] == "active"]

    def hosts(self, only_active: bool = True) -> list[tuple[dict, dict]]:
        src = self.active_clusters if only_active else self.clusters
        return [(c, h) for c in src for h in c["hosts"]]

    def gpu_total(self, only_active: bool = False) -> int:
        src = self.active_clusters if only_active else self.clusters
        return sum(len(c["hosts"]) * c["gpus_per_host"] for c in src)

    def to_inventory(self) -> dict:
        """生成 inventory.yaml 的内容。字段名须与 models.py 的 pydantic 模型对齐。"""
        return {
            "version": 1,
            "defaults": {
                "gpu_count": 8,
                "poll_interval_s": TICK,
                "fallback_group_key": "misc",
                "fallback_group_name": "散装算力域",
            },
            # 标签库：算力域/集群的 badges 里写字符串即按 key 引用这里的定义
            "badge_library": [
                {k: v for k, v in b.items() if v is not None} for b in self.badge_library
            ],
            "capacity_groups": [self._domain_yaml(d) for d in self.domains],
            "clusters": [self._cluster_yaml(c) for c in self.clusters],
        }

    @staticmethod
    def _domain_yaml(d: dict) -> dict:
        out = {k: v for k, v in d.items() if v is not None and k != "badges"}
        if d.get("badges"):
            out["badges"] = [
                b if isinstance(b, str) else {k: v for k, v in b.items() if v is not None}
                for b in d["badges"]
            ]
        return out

    @staticmethod
    def _cluster_yaml(c: dict) -> dict:
        out: dict = {
            "key": c["key"],
            "name": c["name"],
            "sort_order": c["sort_order"],
            "capacity_group": c["domain"],
        }
        if c["status"] != "active":
            out["status"] = c["status"]
        if c.get("note"):
            out["note"] = c["note"]
        if c.get("badges"):
            # 字符串 = 引用标签库；dict = 内联定义（去掉 None 保持 YAML 干净）
            out["badges"] = [
                b if isinstance(b, str) else {k: v for k, v in b.items() if v is not None}
                for b in c["badges"]
            ]
        out["hosts"] = [{
            "key": h["key"],
            # 演示库不真连 SSH，别名给个明显是假的值，避免有人照抄去连
            "ssh_alias": f"demo-{h['key']}",
            "display_name": h["name"],
            "gpu_count": c["gpus_per_host"],
            # 集群级 status 要落到每台机上：前端判"待接入占位卡"看的是
            # host.status（见 overview.js 的 hostRow），只标集群的话这些机器
            # 会显示成"已接入但一直离线"，而不是灰色占位卡。
            **({"status": c["status"]} if c["status"] != "active" else {}),
            **({"vendor": c["vendor"]} if c["vendor"] != "nvidia" else {}),
            "meta": {"gpu_model": c["gpu_model"]},
        } for h in c["hosts"]]
        return out


# ---------------------------------------------------------------------------
# 时序模型：让每种 UI 状态都真实出现，而不是一片均匀噪声
# ---------------------------------------------------------------------------
# 每张卡分配一种"性格"，决定它的利用率曲线形状。
# 比例是刻意配的：要让总览上同时看得到满载(红)、在用(绿)、空占(橙环)、空闲(灰)。
CARD_ROLES = [
    ("hot", 0.22),        # 长期满载，90-100%，热点榜的常客
    ("training", 0.34),   # 常规训练，60-95% 波动，步间有短暂低谷
    ("bursty", 0.14),     # 间歇跑，有活时高、没活时 0
    ("squatted", 0.14),   # 空占：占着大块显存但利用率 ~0（要抓的浪费）
    ("idle", 0.16),       # 真空闲，无进程
]


def pick_roles(rng: random.Random, n: int) -> list[str]:
    """按比例分配角色后打散，避免同一台机器 8 张卡清一色。"""
    roles: list[str] = []
    for name, share in CARD_ROLES:
        roles += [name] * max(1, round(n * share))
    roles = roles[:n] if len(roles) >= n else roles + ["training"] * (n - len(roles))
    rng.shuffle(roles)
    return roles


def diurnal(ts: int) -> float:
    """作息系数：白天忙、深夜闲。让长时间窗的曲线有起伏，不是一条直线。"""
    hour = (ts % 86400) / 3600.0
    # 峰值约在 15 点，谷底约在 4 点；范围 0.55~1.0
    return 0.775 + 0.225 * math.sin((hour - 9.0) / 24.0 * 2 * math.pi)


def util_for(role: str, ts: int, rng: random.Random, phase: float) -> int:
    """给定角色与时刻，产出该次采样的 GPU 利用率(%)。"""
    d = diurnal(ts)
    if role == "hot":
        v = 97 + rng.gauss(0, 2.5)
        # 偶发的 checkpoint 落盘会短暂掉下来
        if rng.random() < 0.02:
            v = rng.uniform(35, 70)
        return int(max(0, min(100, v)))
    if role == "training":
        base = 80 * d + 8 * math.sin(ts / 900.0 + phase)
        v = base + rng.gauss(0, 6)
        if rng.random() < 0.05:      # 训练步之间的空隙
            v *= rng.uniform(0.1, 0.5)
        return int(max(0, min(100, v)))
    if role == "bursty":
        # 以约 40 分钟为周期在"有活/没活"之间切换
        on = math.sin(ts / 2400.0 + phase) > 0.15
        if not on:
            return int(max(0, rng.gauss(1, 1)))
        return int(max(0, min(100, rng.gauss(72 * d, 12))))
    if role == "squatted":
        # 关键：显存占着、算力闲着。util 必须稳定 <5%，否则前端不判定为"空占"
        return int(max(0, min(4, rng.gauss(1.2, 1.0))))
    return int(max(0, rng.gauss(0.4, 0.8)))          # idle


def mem_for(role: str, util: int, total_mib: int, rng: random.Random) -> int:
    """显存占用。空占的特征就是"显存高、利用率低"，两者必须解耦。"""
    if role == "idle":
        return int(rng.uniform(2, 40))               # 驱动/显示占的零头
    if role == "squatted":
        frac = rng.uniform(0.55, 0.92)               # 占着一大块不放
    elif role == "hot":
        frac = rng.uniform(0.80, 0.97)
    elif role == "training":
        frac = rng.uniform(0.55, 0.90)
    else:                                            # bursty
        frac = rng.uniform(0.25, 0.75) if util > 5 else rng.uniform(0.05, 0.2)
    return int(total_mib * frac)


def temp_power(role: str, util: int, rng: random.Random) -> tuple[int, float]:
    """温度/功耗跟利用率正相关 —— 让单卡详情页的三条曲线看起来自洽。"""
    temp = 32 + util * 0.42 + rng.gauss(0, 1.6)
    power = 90 + util * 5.6 + rng.gauss(0, 12)
    return int(max(25, min(92, temp))), round(max(40.0, min(720.0, power)), 1)


# ---------------------------------------------------------------------------
# 建库与写入
# ---------------------------------------------------------------------------
def open_db(path: Path) -> sqlite3.Connection:
    """建库并按"批量导入"调优。

    synchronous=OFF + 大 WAL 只在导入期可接受：这是可重建的演示库，
    崩了重跑就行，不值得为它付每事务 fsync 的代价。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    schema = (_ROOT / "src" / "gpumon" / "db" / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    initialize_demo_database_marker(conn)
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-131072")        # 128MB
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.commit()
    return conn


def write_topology(conn: sqlite3.Connection, topo: Topology) -> dict:
    """写 cluster/host/gpu_card，返回给时序生成用的卡清单。

    这里直接写库而不走 Store.sync_topology()：那条路要求 inventory.yaml 已经
    是"当前生效配置"（走 load_inventory 的 lru_cache），而我们要生成的库可能
    和用户现有配置无关。字段与 schema 对齐即可，逻辑很薄。
    """
    cards: list[dict] = []
    with conn:
        for c in topo.clusters:
            conn.execute("INSERT INTO cluster(key,name,sort_order) VALUES(?,?,?)",
                         (c["key"], c["name"], c["sort_order"]))
            cid = conn.execute("SELECT id FROM cluster WHERE key=?", (c["key"],)).fetchone()[0]
            for i, h in enumerate(c["hosts"]):
                conn.execute(
                    "INSERT INTO host(cluster_id,key,ssh_alias,display_name,gpu_count,meta_json,sort_order)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (cid, h["key"], f"demo-{h['key']}", h["name"], c["gpus_per_host"],
                     json.dumps({"gpu_model": c["gpu_model"]}, ensure_ascii=False), i))
                hid = conn.execute("SELECT id FROM host WHERE key=?", (h["key"],)).fetchone()[0]
                # planned/retired 的机器不建卡：planned 本来就没接入；retired 保留
                # 拓扑行但不再有卡级数据，正好对应"停采但留历史"的语义。
                if c["status"] != "active":
                    continue
                for gi in range(c["gpus_per_host"]):
                    uuid = (f"GPU-DEMO-{h['key']}-{gi}" if c["vendor"] == "nvidia"
                            else f"AMD-DEMO-{h['key']}-{gi}")
                    gid = conn.execute(
                        "INSERT INTO gpu_card(host_id,gpu_index,uuid,name,mem_total_mib)"
                        " VALUES(?,?,?,?,?) RETURNING id",
                        (hid, gi, uuid, c["gpu_model"], mem_total(c))).fetchone()[0]
                    cards.append({"gpu_id": gid, "host_id": hid, "host_key": h["key"],
                                  "cluster": c["key"], "mem_total": mem_total(c)})
    return {"cards": cards}


def mem_total(c: dict) -> int:
    """该集群单卡显存(MiB)。fixtures 可以显式给 mem_total_mib，没给就从型号名里猜。"""
    if c.get("mem_total_mib"):
        return int(c["mem_total_mib"])
    m = re.search(r"(\d+)\s*GB", c.get("gpu_model") or "", re.I)
    return int(m.group(1)) * 1024 if m else 81920


def assign_users(rng: random.Random, cards: list[dict]) -> dict[int, dict]:
    """给每张"有人用"的卡分配一个使用人。

    按 weight 抽样，让排行榜有明确的头部和长尾；style 与卡的角色挂钩
    （squatter 优先落在 squatted 卡上），这样"谁在空占"能对上号。
    """
    users = FX.USERS
    by_style: dict[str, list[dict]] = {}
    for u in users:
        by_style.setdefault(u["style"], []).append(u)

    def pick(prefer: str | None) -> dict:
        pool = by_style.get(prefer) or users
        weights = [u["weight"] for u in pool]
        return rng.choices(pool, weights=weights, k=1)[0]

    owner: dict[int, dict] = {}
    for c in cards:
        role = c["role"]
        if role == "idle":
            continue                      # 空闲卡没有进程
        prefer = {"squatted": "squatter", "bursty": "burster",
                  "hot": "trainer", "training": "trainer"}.get(role)
        owner[c["gpu_id"]] = pick(prefer)
    return owner


def generate(conn: sqlite3.Connection, cards: list[dict], days: float,
             now: int, rng: random.Random, quiet: bool = False) -> dict:
    """造时序并写入三张事实表。返回各表行数。"""
    steps = int(days * 86400 / TICK)
    start = now - steps * TICK

    # 每张卡定一次角色与相位；相位让同机各卡的曲线不完全同步
    roles = pick_roles(rng, len(cards))
    for c, r in zip(cards, roles):
        c["role"] = r
        c["phase"] = rng.uniform(0, 2 * math.pi)
        c["pid"] = rng.randint(1000, 65000)
        c["comm"] = rng.choice(FX.PROC_NAMES)

    owner = assign_users(rng, cards)

    # 主机级：按 host 聚合它名下各卡的负载，CPU/内存跟着动
    hosts: dict[int, list[dict]] = {}
    for c in cards:
        hosts.setdefault(c["host_id"], []).append(c)
    host_meta = {hid: {"ncpu": rng.choice([96, 128, 192, 256]),
                       "mem_total": rng.choice([1024, 2048]) * 1024}
                 for hid in hosts}

    gpu_rows: list[tuple] = []
    proc_rows: list[tuple] = []
    host_rows: list[tuple] = []
    counts = {"sample_gpu": 0, "sample_proc": 0, "sample_host": 0}

    def flush(force: bool = False) -> None:
        nonlocal gpu_rows, proc_rows, host_rows
        if not force and len(gpu_rows) < FLUSH_ROWS:
            return
        with conn:
            if gpu_rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO sample_gpu"
                    "(gpu_id,ts,util_gpu,util_mem,mem_used_mib,temp_c,power_w)"
                    " VALUES(?,?,?,?,?,?,?)", gpu_rows)
            if proc_rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO sample_proc"
                    "(gpu_id,ts,pid,username,comm,mem_used_mib) VALUES(?,?,?,?,?,?)", proc_rows)
            if host_rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO sample_host"
                    "(host_id,ts,ncpu,load1,load5,load15,cpu_util_pct,"
                    "mem_total_mib,mem_avail_mib,mem_used_mib) VALUES(?,?,?,?,?,?,?,?,?,?)", host_rows)
        counts["sample_gpu"] += len(gpu_rows)
        counts["sample_proc"] += len(proc_rows)
        counts["sample_host"] += len(host_rows)
        gpu_rows, proc_rows, host_rows = [], [], []

    next_report = 0.1
    for i in range(steps):
        ts = start + i * TICK
        for c in cards:
            util = util_for(c["role"], ts, rng, c["phase"])
            mem = mem_for(c["role"], util, c["mem_total"], rng)
            temp, power = temp_power(c["role"], util, rng)
            # util_mem（显存带宽利用率）与算力利用率相关但更低
            umem = int(max(0, min(100, util * rng.uniform(0.3, 0.6))))
            gpu_rows.append((c["gpu_id"], ts, util, umem, mem, temp, power))
            u = owner.get(c["gpu_id"])
            if u is not None and mem > 64:
                proc_rows.append((c["gpu_id"], ts, c["pid"], u["name"], c["comm"], mem))

        for hid, hcards in hosts.items():
            meta = host_meta[hid]
            avg_util = sum(util_for(c["role"], ts, rng, c["phase"]) for c in hcards) / len(hcards)
            cpu = max(1.0, min(99.0, avg_util * 0.55 + rng.gauss(8, 4)))
            load1 = max(0.1, meta["ncpu"] * cpu / 100.0 + rng.gauss(0, 2))
            used = int(meta["mem_total"] * min(0.95, 0.18 + avg_util / 160.0))
            host_rows.append((hid, ts, meta["ncpu"], round(load1, 2),
                              round(load1 * 0.95, 2), round(load1 * 0.9, 2), round(cpu, 1),
                              meta["mem_total"], meta["mem_total"] - used, used))
        flush()

        if not quiet and steps > 200 and i / steps >= next_report:
            # 报"已生成"而不是"已写入"：行是攒够 FLUSH_ROWS 才落库的，
            # 只报 counts 会在两次 flush 之间一直显示同一个数，看着像卡住。
            made = counts["sample_gpu"] + len(gpu_rows)
            print(f"  造数进度 {i/steps*100:5.1f}%  已生成 {made:,} 行 GPU 样本", flush=True)
            next_report += 0.1

    flush(force=True)
    return counts


def write_collector_status(conn: sqlite3.Connection, topo: Topology, now: int,
                           rng: random.Random) -> None:
    """写 collector_status，让健康灯与主机页的"在线/离线"有依据。

    刻意留一台"刚掉线"的机器：离线态是最容易做错的 UI 分支
    （必须显示"离线"而不是最后一次的陈旧占用值），演示库里得有实例可看。
    """
    hosts = topo.hosts(only_active=True)
    offline_idx = len(hosts) - 1 if len(hosts) > 3 else -1
    with conn:
        for i, (c, h) in enumerate(hosts):
            hid = conn.execute("SELECT id FROM host WHERE key=?", (h["key"],)).fetchone()[0]
            n_gpu = c["gpus_per_host"]
            if i == offline_idx:
                # 20 分钟前最后一次成功 → 远超 120s 在线阈值，判离线
                last_ok = now - 1200
                conn.execute(
                    "INSERT INTO collector_status(host_id,last_try_ts,last_ok_ts,gpus_seen,"
                    "consec_fail,last_error) VALUES(?,?,?,?,?,?)",
                    (hid, now - 5, last_ok, n_gpu, 39,
                     "超时(>20s)  # 演示数据：这台故意做成离线"))
            else:
                # 再留一台"少一张卡"的，用于演示掉卡检测
                seen = n_gpu - 1 if i == 0 and n_gpu > 1 else n_gpu
                conn.execute(
                    "INSERT INTO collector_status(host_id,last_try_ts,last_ok_ts,gpus_seen,"
                    "consec_fail,last_error) VALUES(?,?,?,?,?,?)",
                    (hid, now - rng.randint(1, 25), now - rng.randint(1, 25), seen, 0, None))


def build_rollups(db: Path, now: int, quiet: bool = False) -> dict:
    """调项目自己的 Rollup 生成聚合表 —— 口径必须和生产一致，不能自己写一份。"""
    from gpumon.db.rollup import Rollup
    from gpumon.db.store import Store

    store = Store(db)
    # 水位从 0 起，一次把全部历史聚上来
    Rollup(store).roll_all(now)
    conn = store.write_conn()
    out = {}
    for t in ("rollup_gpu_5m", "rollup_gpu_1h", "rollup_host_1h"):
        out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.commit()
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gen_demo_db.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="生成演示数据库 + 配套 inventory（无需任何真实 GPU 机器）",
        epilog="""示例：
  # 小规模试跑（2 域 / 3 集群 / 6 机 / 48 卡，1 天历史）
  uv run python scripts/gen_demo_db.py --db data/demo.db --inventory config/inventory.demo.yaml

  # 大规模压测（4 域 / 32 机 / 256 卡，3 天历史）
  uv run python scripts/gen_demo_db.py --scale large --days 3 \\
      --db data/demo.db --inventory config/inventory.demo.yaml

  # 看效果（把生成的清单和库指给服务）
  cp config/inventory.demo.yaml config/inventory.yaml
  # 并把 config/settings.toml 的 [db] path 指向 data/demo.db
  uv run gpumon web
""")
    p.add_argument("--scale", choices=["small", "large"], default="small",
                   help="small=48 卡（默认），large=256 卡")
    p.add_argument("--days", type=float, default=3.0,
                   help="造多少天历史（默认 3；想让 1 月窗口有数据用 31）")
    p.add_argument("--db", default="data/demo.db", help="输出数据库路径")
    p.add_argument("--inventory", default="config/inventory.demo.yaml",
                   help="同时生成的 inventory YAML 路径")
    p.add_argument("--seed", type=int, default=20260810, help="随机种子，保证可复现")
    p.add_argument("--force", action="store_true", help="覆盖已存在的输出文件")
    p.add_argument("--quiet", action="store_true", help="少打印")
    return p


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (_ROOT / p)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        db = assert_safe_generation_target(resolve(args.db), kind="database")
        inv_path = assert_safe_generation_target(resolve(args.inventory), kind="inventory")
        if db == inv_path:
            raise DemoSafetyError("数据库和 inventory 不能写到同一个路径")
    except DemoSafetyError as exc:
        print(f"拒绝生成：{exc}", file=sys.stderr)
        return 2

    for target in (db, inv_path):
        if not target.exists():
            continue
        if not args.force:
            print(f"{target} 已存在。加 --force 覆盖。", file=sys.stderr)
            return 2
        marked = demo_database_state(target) is not None if target == db else is_demo_inventory(target)
        if not marked:
            print(f"拒绝覆盖没有 demo 生成标记的文件: {target}", file=sys.stderr)
            return 2

    sidecars = [db.with_name(db.name + suffix) for suffix in ("-wal", "-shm")]
    if not db.exists() and any(side.exists() for side in sidecars):
        print("拒绝删除没有对应已标记 demo 主库的 SQLite sidecar", file=sys.stderr)
        return 2

    FX.validate()
    if args.scale == "large":
        domains, clusters = FX.DOMAINS, FX.CLUSTERS
    else:
        domains, clusters = FX.SMALL["domains"], FX.SMALL["clusters"]
    topo = Topology(domains, clusters, FX.BADGE_LIBRARY)

    n_hosts = len(topo.hosts(only_active=False))
    n_gpu_active = topo.gpu_total(only_active=True)
    steps = int(args.days * 86400 / TICK)
    est_rows = steps * (n_gpu_active + n_hosts)
    if not args.quiet:
        print(f"规模 {args.scale}：{len(domains)} 算力域 / {len(clusters)} 集群 / "
              f"{n_hosts} 机 / {topo.gpu_total()} 卡（在采 {n_gpu_active} 卡）")
        print(f"历史 {args.days} 天 x {TICK}s → 约 {est_rows:,} 行事实数据")
        if est_rows > 8_000_000:
            print("  （行数较多，预计需要几分钟，且库会到 GB 级）")

    rng = random.Random(args.seed)
    t0 = time.time()

    for target in (db, inv_path):
        if target.exists():
            target.unlink()
    for side in sidecars:
        if side.exists():
            side.unlink()

    inv_path.parent.mkdir(parents=True, exist_ok=True)
    inv_doc = topo.to_inventory()
    inv_path.write_text(
        DEMO_INVENTORY_MARKER + "\n"
        "# 演示清单 —— 由 scripts/gen_demo_db.py 生成，内容是虚构的搞怪示例。\n"
        "# 想看真实效果：把本文件复制成 config/inventory.yaml，\n"
        f"# 并把 config/settings.toml 的 [db] path 指向 {args.db}。\n"
        + yaml.safe_dump(inv_doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8")
    # 生成的清单必须能过项目自己的校验，否则演示第一步就报错
    from gpumon.config import _validate_unique_keys
    from gpumon.models import Inventory
    _validate_unique_keys(Inventory.model_validate(inv_doc))

    now = int(time.time())
    conn = open_db(db)
    cards = write_topology(conn, topo)["cards"]
    counts = generate(conn, cards, args.days, now, rng, quiet=args.quiet)
    write_collector_status(conn, topo, now, rng)
    conn.commit()
    conn.close()

    roll = build_rollups(db, now, quiet=args.quiet)
    finalize_demo_database(db)
    elapsed = time.time() - t0

    if not args.quiet:
        size_mb = db.stat().st_size / (1024 * 1024)
        print("\n完成：")
        for k, v in counts.items():
            print(f"  {k:14s} {v:>12,} 行")
        for k, v in roll.items():
            print(f"  {k:14s} {v:>12,} 行")
        print(f"  数据库          {size_mb:>11.1f} MB")
        print(f"  用户            {len(FX.USERS):>12,} 人")
        print(f"  耗时            {elapsed:>11.1f} s")
        print(f"\n清单已写入 {inv_path}")
        print("\n查看效果：")
        # 输出路径可能在项目外（比如 /tmp），relative_to 会抛异常，故退回绝对路径
        try:
            shown = inv_path.relative_to(_ROOT)
        except ValueError:
            shown = inv_path
        print(f"  cp {shown} config/inventory.yaml")
        print(f"  # 把 config/settings.toml 的 [db] path 改成 {args.db}")
        print("  uv run gpumon web        # 然后开 http://127.0.0.1:8848/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
