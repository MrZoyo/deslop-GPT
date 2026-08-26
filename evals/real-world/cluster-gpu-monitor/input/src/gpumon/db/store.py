"""存储层（DB 抽象）。

职责：建库、同步拓扑、写一轮采样、以及给 API 用的所有查询。
把 DB 细节集中在这里，API/前端不直接碰 SQL —— 将来迁 TimescaleDB 只改本文件。

并发模型：采集器是唯一写者（单线程循环），持有一个持久写连接；
查询为只读，每次开新连接（FastAPI 同步路由在线程池执行，互不干扰）。
SQLite 开 WAL，读写不互相阻塞。
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Collection
from pathlib import Path

from ..config import db_path, load_inventory, load_settings
from ..models import ProbeResult

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# 时间窗 → 秒
WINDOWS: dict[str, int] = {
    "12h": 12 * 3600,
    "24h": 24 * 3600,
    "48h": 48 * 3600,
    "72h": 72 * 3600,
    "1w": 7 * 24 * 3600,
    "2w": 14 * 24 * 3600,
    "1m": 30 * 24 * 3600,
}

# metric → (rollup 表的均值列, 最大值列或 None)
_METRIC_COLS: dict[str, tuple[str, str | None]] = {
    "util_gpu": ("util_gpu_avg", "util_gpu_max"),
    "util_mem": ("util_mem_avg", None),
    "mem_used": ("mem_used_avg", "mem_used_max"),
    "temp": ("temp_avg", "temp_max"),
    "power": ("power_avg", None),
}

# scope → (聚合分组键 SQL, 该键的标签列)
# 都基于 rollup_gpu_* join gpu_card→host→cluster
_SCOPE_GROUP: dict[str, str | None] = {
    "gpu": "g.id",
    "host": "h.id",
    "cluster": "c.id",
    "global": None,
}

# HTTP 层和存储层共用同一组白名单。路由会把非法输入转换成明确的 4xx，
# Store 仍保留独立校验，避免脚本或将来的非 HTTP 调用绕过边界。
METRICS = tuple(_METRIC_COLS)
SCOPES = tuple(_SCOPE_GROUP)
USER_TOP_SORTS = ("gpu_hours", "mem_gb_peak")


class _ClosingConnection(sqlite3.Connection):
    """完成事务上下文后关闭临时查询连接。"""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def pick_table(window_seconds: int) -> tuple[str, int]:
    """按窗口选聚合表：≤24h 用 5 分钟桶，否则用 1 小时桶。返回 (表名, 桶宽秒)。"""
    if window_seconds <= 24 * 3600:
        return "rollup_gpu_5m", 300
    return "rollup_gpu_1h", 3600


def current_sample_max_age_s() -> int:
    """实时视图允许的最大样本年龄；至少容忍四轮采集或两分钟。"""
    return max(120, load_settings().collector.poll_interval_s * 4)


def _active_inventory_capacity() -> tuple[dict[str, int], dict[str, int]]:
    """返回 active 主机/集群的预期 GPU 数，inventory 是唯一事实来源。

    planned 尚未接入，retired 只保留历史；两者既不应把 coverage 分母撑大，
    其旧观测也不应继续混入当前统计口径。集群被标为非 active 时，其下主机即使
    没有逐台重复标记，也按同一状态处理。
    """
    inv = load_inventory()
    by_host: dict[str, int] = {}
    by_cluster: dict[str, int] = {}
    for cluster in inv.clusters:
        if cluster.status != "active":
            continue
        for host in cluster.hosts:
            if host.status != "active":
                continue
            expected = host.gpu_count or inv.defaults.gpu_count
            by_host[host.key] = expected
            by_cluster[cluster.key] = by_cluster.get(cluster.key, 0) + expected
    return by_host, by_cluster


class Store:
    def __init__(self, path: str | Path | None = None, *, read_only: bool = False,
                 query_timeout_s: float | None = None):
        self.path = Path(path) if path else db_path()
        self.read_only = read_only
        self.query_timeout_s = query_timeout_s
        self._write_conn: sqlite3.Connection | None = None
        self._host_id: dict[str, int] = {}   # host.key -> host.id 缓存

    # ---- 连接 ---------------------------------------------------------------
    def _new_conn(self, *, close_on_exit: bool = False) -> sqlite3.Connection:
        factory = _ClosingConnection if close_on_exit else sqlite3.Connection
        if self.read_only:
            # mode=ro 是 SQLite 文件层面的强制只读；as_uri() 会安全转义路径里的
            # 空格、问号等 URI 特殊字符。只读进程不得顺手创建目录或空数据库。
            uri = f"{self.path.resolve().as_uri()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=15, factory=factory)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, timeout=15, factory=factory)
        conn.row_factory = sqlite3.Row
        if self.read_only:
            # 即使以后连接构造方式被误改，query_only 仍会拦住该连接上的 SQL 写入。
            conn.execute("PRAGMA query_only=ON")
        else:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        # 查询是「每次开新连接」，私有 page cache 每次都是冷的。mmap 让读走 OS page
        # cache（进程间共享、可被内核回收），跨连接复用，比调大 cache_size 更省内存
        # ——部署机只有 ~900MB RAM，每连接私有缓存会乘以线程池大小。
        conn.execute("PRAGMA mmap_size=268435456")   # 256MB 上限，按需映射不预占
        if self.read_only and self.query_timeout_s is not None:
            deadline = time.monotonic() + self.query_timeout_s
            conn.set_progress_handler(
                lambda: int(time.monotonic() >= deadline),
                10_000,
            )
        return conn

    def write_conn(self) -> sqlite3.Connection:
        if self.read_only:
            raise RuntimeError("只读 Store 不允许获取写连接")
        if self._write_conn is None:
            self._write_conn = self._new_conn()
            self._write_conn.execute("PRAGMA synchronous=NORMAL")  # WAL 下足够安全且更快
        return self._write_conn

    def connect(self) -> sqlite3.Connection:
        """打开临时查询连接；``with`` 退出时提交/回滚并关闭。

        只有以 ``read_only=True`` 构造的 Store 才会由 SQLite 强制只读；采集器的
        普通 Store 仍允许在同一数据库上完成读写事务。直接调用方仍可手工关闭，
        但内部查询必须使用 ``with``，避免连接及其 mmap 等待垃圾回收。
        """
        return self._new_conn(close_on_exit=True)

    # ---- 建库与拓扑 ---------------------------------------------------------
    def init_schema(self) -> None:
        conn = self.write_conn()
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()

    def sync_topology(self) -> None:
        """按 inventory 幂等 upsert cluster/host（按 key），不删历史。"""
        inv = load_inventory()
        conn = self.write_conn()
        with conn:
            for c in inv.clusters:
                conn.execute(
                    "INSERT INTO cluster(key,name,sort_order) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET name=excluded.name, sort_order=excluded.sort_order",
                    (c.key, c.name, c.sort_order),
                )
                cid = conn.execute("SELECT id FROM cluster WHERE key=?", (c.key,)).fetchone()[0]
                for i, h in enumerate(c.hosts):
                    gc = h.gpu_count or inv.defaults.gpu_count
                    conn.execute(
                        "INSERT INTO host(cluster_id,key,ssh_alias,display_name,gpu_count,meta_json,sort_order) "
                        "VALUES(?,?,?,?,?,?,?) "
                        "ON CONFLICT(key) DO UPDATE SET cluster_id=excluded.cluster_id, "
                        "ssh_alias=excluded.ssh_alias, display_name=excluded.display_name, "
                        "gpu_count=excluded.gpu_count, meta_json=excluded.meta_json, sort_order=excluded.sort_order",
                        (cid, h.key, h.ssh_alias, h.display_name, gc, json.dumps(h.meta, ensure_ascii=False), i),
                    )
        self._host_id.clear()

    def host_id(self, conn: sqlite3.Connection, host_key: str) -> int:
        if host_key not in self._host_id:
            row = conn.execute("SELECT id FROM host WHERE key=?", (host_key,)).fetchone()
            if row is None:
                raise KeyError(f"未知主机 key（请先 sync_topology）: {host_key}")
            self._host_id[host_key] = row[0]
        return self._host_id[host_key]

    def _upsert_gpu(self, conn, host_id: int, g) -> int:
        """按 uuid upsert 一张卡，返回 gpu_card.id。"""
        row = conn.execute(
            "INSERT INTO gpu_card(host_id,gpu_index,uuid,name,mem_total_mib) VALUES(?,?,?,?,?) "
            "ON CONFLICT(uuid) DO UPDATE SET host_id=excluded.host_id, gpu_index=excluded.gpu_index, "
            "name=excluded.name, mem_total_mib=excluded.mem_total_mib RETURNING id",
            (host_id, g.index, g.uuid, g.name, g.mem_total_mib),
        ).fetchone()
        return row[0]

    # ---- 写一轮采样 ---------------------------------------------------------
    def record_round(self, ts: int, results: list[ProbeResult]) -> None:
        conn = self.write_conn()
        with conn:  # 单事务
            for r in results:
                hid = self.host_id(conn, r.host_key)
                if not r.ok:
                    conn.execute(
                        "INSERT INTO collector_status(host_id,last_try_ts,consec_fail,last_error) "
                        "VALUES(?,?,1,?) ON CONFLICT(host_id) DO UPDATE SET "
                        "last_try_ts=excluded.last_try_ts, consec_fail=collector_status.consec_fail+1, "
                        "last_error=excluded.last_error",
                        (hid, ts, (r.error or "")[:500]),
                    )
                    continue

                uuid2id: dict[str, int] = {}
                for g in r.gpus:
                    uuid2id[g.uuid] = self._upsert_gpu(conn, hid, g)

                conn.executemany(
                    "INSERT OR IGNORE INTO sample_gpu(gpu_id,ts,util_gpu,util_mem,mem_used_mib,temp_c,power_w) "
                    "VALUES(?,?,?,?,?,?,?)",
                    [(uuid2id[g.uuid], ts, g.util_gpu, g.util_mem, g.mem_used_mib, g.temp_c, g.power_w)
                     for g in r.gpus],
                )
                procs = [(uuid2id[p.gpu_uuid], ts, p.pid, p.username, p.comm, p.mem_used_mib)
                         for p in r.procs if p.gpu_uuid in uuid2id]
                if procs:
                    conn.executemany(
                        "INSERT OR IGNORE INTO sample_proc(gpu_id,ts,pid,username,comm,mem_used_mib) "
                        "VALUES(?,?,?,?,?,?)", procs)
                if r.host:
                    hs = r.host
                    conn.execute(
                        "INSERT OR IGNORE INTO sample_host(host_id,ts,ncpu,load1,load5,load15,cpu_util_pct,"
                        "mem_total_mib,mem_avail_mib,mem_used_mib) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (hid, ts, hs.ncpu, hs.load1, hs.load5, hs.load15, hs.cpu_util_pct,
                         hs.mem_total_mib, hs.mem_avail_mib, hs.mem_used_mib))

                conn.execute(
                    "INSERT INTO collector_status(host_id,last_try_ts,last_ok_ts,gpus_seen,consec_fail,last_error) "
                    "VALUES(?,?,?,?,0,?) ON CONFLICT(host_id) DO UPDATE SET "
                    "last_try_ts=excluded.last_try_ts, last_ok_ts=excluded.last_ok_ts, "
                    "gpus_seen=excluded.gpus_seen, consec_fail=0, "
                    "last_error=excluded.last_error",
                    (hid, ts, ts, len(r.gpus), (r.warning or "")[:500] or None))

    # ---- 查询：拓扑 ---------------------------------------------------------
    def get_topology(self) -> list[dict]:
        with self.connect() as conn:
            clusters = conn.execute(
                "SELECT id,key,name,sort_order FROM cluster ORDER BY sort_order,id").fetchall()
            hosts = conn.execute(
                "SELECT id,cluster_id,key,ssh_alias,display_name,gpu_count,sort_order "
                "FROM host ORDER BY sort_order,id").fetchall()
            gpus = conn.execute(
                "SELECT id,host_id,gpu_index,uuid,name,mem_total_mib FROM gpu_card "
                "ORDER BY host_id,gpu_index").fetchall()
        gpus_by_host: dict[int, list] = {}
        for g in gpus:
            gpus_by_host.setdefault(g["host_id"], []).append(dict(g))
        hosts_by_cluster: dict[int, list] = {}
        for h in hosts:
            d = dict(h)
            d["gpus"] = gpus_by_host.get(h["id"], [])
            hosts_by_cluster.setdefault(h["cluster_id"], []).append(d)
        out = []
        for c in clusters:
            d = dict(c)
            d["hosts"] = hosts_by_cluster.get(c["id"], [])
            out.append(d)
        return out

    # ---- 查询：实时快照 -----------------------------------------------------
    def get_snapshot(self) -> dict:
        """每卡最近一条 sample_gpu + 每机最近 sample_host + 每卡当前进程。

        实现要点 —— 别改回 `GROUP BY` 写法：事实表是 WITHOUT ROWID、主键
        `(gpu_id, ts)` / `(host_id, ts)`，所以「某实体的最后一条」用
        `WHERE id=? ORDER BY ts DESC LIMIT 1` 直接走主键**尾部 seek**，O(log N)。

        早期版本写成 `JOIN (SELECT id, MAX(ts) ... GROUP BY id)`，那是**全表扫 +
        临时 B-tree**，代价随库大小线性增长：610MB 库（sample_gpu 5.3M 行、
        sample_proc 3.9M 行）上单这一条要 18 秒，三条合计约 30 秒，而 /api/overview
        每次刷新都调本函数 → 网页整体 50s+ 打不开。实体只有几十个（卡 72、机 9），
        逐个 seek 总耗时约 35ms，比一次全表扫快三个数量级。
        """
        with self.connect() as conn:
            gpu_ids = [r[0] for r in conn.execute("SELECT id FROM gpu_card")]
            host_ids = [r[0] for r in conn.execute("SELECT id FROM host")]

            gpus: dict[int, dict] = {}
            for gid in gpu_ids:
                row = conn.execute(
                    "SELECT gpu_id, ts, util_gpu, util_mem, mem_used_mib, temp_c, power_w "
                    "FROM sample_gpu WHERE gpu_id=? ORDER BY ts DESC LIMIT 1", (gid,)
                ).fetchone()
                if row is not None:
                    gpus[gid] = dict(row)

            hosts: dict[int, dict] = {}
            for hid in host_ids:
                row = conn.execute(
                    "SELECT host_id, ts, ncpu, load1, load5, load15, cpu_util_pct, "
                    "mem_total_mib, mem_avail_mib, mem_used_mib "
                    "FROM sample_host WHERE host_id=? ORDER BY ts DESC LIMIT 1", (hid,)
                ).fetchone()
                if row is not None:
                    hosts[hid] = dict(row)

            # 进程必须属于该卡最新 GPU 样本的同一轮。没有进程的轮次不会写 sample_proc；
            # 若独立取 sample_proc 的 MAX(ts)，任务退出后就会把上一轮进程永久当成当前进程。
            procs_by_gpu: dict[int, list] = {}
            for gid, gpu_sample in gpus.items():
                rows = conn.execute(
                    "SELECT gpu_id, pid, username, comm, mem_used_mib FROM sample_proc "
                    "WHERE gpu_id=? AND ts=?", (gid, gpu_sample["ts"])
                ).fetchall()
                if rows:
                    procs_by_gpu[gid] = [dict(r) for r in rows]

        return {"gpus": gpus, "hosts": hosts, "procs": procs_by_gpu}

    # ---- 查询：近期利用率（卡片大字/底色用） -------------------------------
    def get_util_recent(self, now: int | None = None, window_s: int = 600,
                        idle_eps: float = 5.0, idle_streak: int = 3) -> dict[int, float]:
        """每卡「近期利用率」：最近 window_s 秒 util_gpu 的均值。

        用于卡片大字/底色，抹平训练步之间 0/100 的瞬时抖动。附一条「置零」规则：
        最近 idle_streak 个样本全部 ≤ idle_eps 时直接归 0——否则任务刚停时 10 分钟
        均值仍挂着高位（下降沿迟滞），会误显示"卡还在用"。

        直接读原始 sample_gpu（永远最新鲜，不依赖 rollup）。返回 {gpu_id: 近期值}；
        窗口内无样本的卡不出现，调用方按缺省=None 处理。离线主机的置空由调用方负责
        （这里只按样本算，不看在线状态）。
        """
        now = int(now or time.time())
        since = now - window_s
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT gpu_id, util_gpu FROM sample_gpu "
                "WHERE ts >= ? AND ts < ? ORDER BY gpu_id, ts",
                (since, now),
            ).fetchall()
        by_gpu: dict[int, list[int]] = {}
        for r in rows:
            if r["util_gpu"] is None:   # nvidia-smi 偶尔 N/A，跳过不参与均值/置零判定
                continue
            by_gpu.setdefault(r["gpu_id"], []).append(r["util_gpu"])
        out: dict[int, float] = {}
        for gid, utils in by_gpu.items():
            tail = utils[-idle_streak:]   # 已按 ts 升序，尾部即最近几次
            if len(tail) >= idle_streak and all(u <= idle_eps for u in tail):
                out[gid] = 0.0
            else:
                out[gid] = round(sum(utils) / len(utils), 1)
        return out

    # ---- 查询：时间窗加权平均 ----------------------------------------------
    def get_avg(self, window: str, scope: str, metric: str, now: int | None = None) -> list[dict]:
        """返回 scope 下每个实体在 window 内的加权平均/最大/coverage。"""
        if window not in WINDOWS:
            raise ValueError(f"未知窗口: {window}")
        if metric not in _METRIC_COLS:
            raise ValueError(f"未知指标: {metric}")
        if scope not in _SCOPE_GROUP:
            raise ValueError(f"未知 scope: {scope}")
        now = int(now or time.time())
        win = WINDOWS[window]
        since = now - win
        table, _ = pick_table(win)
        avg_col, max_col = _METRIC_COLS[metric]
        interval = load_settings().collector.poll_interval_s
        expected_per_gpu = win / interval
        expected_by_host, expected_by_cluster = _active_inventory_capacity()
        active_host_keys = list(expected_by_host)
        if not active_host_keys:
            return []

        group = _SCOPE_GROUP[scope]
        max_expr = f"MAX(r.{max_col})" if max_col else "NULL"
        select_id = f"{group} AS gid," if group else ""
        group_by = f"GROUP BY {group}" if group else ""
        host_placeholders = ",".join("?" for _ in active_host_keys)
        sql = f"""
            SELECT {select_id}
                   SUM(r.{avg_col}*r.n)/NULLIF(SUM(r.n),0) AS avg,
                   {max_expr} AS mx,
                   SUM(r.n) AS sum_n,
                   h.key AS host_key, h.display_name AS host_name,
                   c.key AS cluster_key, c.name AS cluster_name, g.gpu_index AS gpu_index
            FROM {table} r
            JOIN gpu_card g ON g.id=r.gpu_id
            JOIN host h ON h.id=g.host_id
            JOIN cluster c ON c.id=h.cluster_id
            WHERE r.bucket_ts >= ? AND r.bucket_ts < ?
                  AND h.key IN ({host_placeholders})
            {group_by}
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (since, now, *active_host_keys)).fetchall()
        out = []
        for r in rows:
            if scope == "gpu":
                n_gpus = 1
            elif scope == "host":
                n_gpus = expected_by_host.get(r["host_key"], 0)
            elif scope == "cluster":
                n_gpus = expected_by_cluster.get(r["cluster_key"], 0)
            else:
                n_gpus = sum(expected_by_host.values())
            if n_gpus <= 0:
                continue
            expected = n_gpus * expected_per_gpu
            cov = min(1.0, (r["sum_n"] or 0) / expected) if expected else 0.0
            item = {
                "avg": round(r["avg"], 1) if r["avg"] is not None else None,
                "max": r["mx"],
                "coverage": round(cov, 3),
                "n_gpus": n_gpus,
            }
            if scope == "gpu":
                item.update(gpu_id=r["gid"], gpu_index=r["gpu_index"],
                            host=r["host_key"], cluster=r["cluster_key"])
            elif scope == "host":
                item.update(host_id=r["gid"], host=r["host_key"],
                            host_name=r["host_name"], cluster=r["cluster_key"])
            elif scope == "cluster":
                item.update(cluster_id=r["gid"], cluster=r["cluster_key"], cluster_name=r["cluster_name"])
            out.append(item)
        return out

    def get_avg_multi(self, scope: str, metric: str, now: int | None = None) -> dict:
        """每实体一次性返回全部 7 个窗口的平均，供总览对比表。"""
        if scope not in _SCOPE_GROUP:
            raise ValueError(f"未知 scope: {scope}")
        if metric not in _METRIC_COLS:
            raise ValueError(f"未知指标: {metric}")
        now = int(now or time.time())
        result: dict[str, list[dict]] = {}
        for w in WINDOWS:
            result[w] = self.get_avg(w, scope, metric, now=now)
        return result

    # ---- 查询：时序 ---------------------------------------------------------
    def get_series(self, scope: str, entity_id: int | None, metric: str,
                   window: str, now: int | None = None) -> list[list]:
        """返回 [[bucket_ts, avg], ...]，断档桶不出现（前端 connectNulls=false 自然断开）。"""
        if window not in WINDOWS:
            raise ValueError(f"未知窗口: {window}")
        if metric not in _METRIC_COLS:
            raise ValueError(f"未知指标: {metric}")
        if scope not in _SCOPE_GROUP:
            raise ValueError(f"未知 scope: {scope}")
        if scope == "global":
            if entity_id is not None:
                raise ValueError("global scope 不接受 entity_id")
        elif not isinstance(entity_id, int) or isinstance(entity_id, bool) or entity_id < 1:
            raise ValueError(f"{scope} scope 需要正整数 entity_id")
        now = int(now or time.time())
        win = WINDOWS[window]
        since = now - win
        table, _ = pick_table(win)
        avg_col, _ = _METRIC_COLS[metric]
        filt, params = "", [since, now]
        if scope == "gpu":
            filt = "AND g.id=?"
            params.append(entity_id)
        elif scope == "host":
            filt = "AND h.id=?"
            params.append(entity_id)
        elif scope == "cluster":
            filt = "AND c.id=?"
            params.append(entity_id)
        sql = f"""
            SELECT r.bucket_ts AS b, SUM(r.{avg_col}*r.n)/NULLIF(SUM(r.n),0) AS v
            FROM {table} r
            JOIN gpu_card g ON g.id=r.gpu_id
            JOIN host h ON h.id=g.host_id
            JOIN cluster c ON c.id=h.cluster_id
            WHERE r.bucket_ts >= ? AND r.bucket_ts < ? {filt}
            GROUP BY r.bucket_ts ORDER BY r.bucket_ts
        """
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [[r["b"], round(r["v"], 1) if r["v"] is not None else None] for r in rows]

    # ---- 查询：使用人 -------------------------------------------------------
    def get_users_top(self, window: str, by: str = "gpu_hours", limit: int = 20,
                      cluster_key: str | None = None, now: int | None = None,
                      excluded_host_keys: Collection[str] | None = None) -> list[dict]:
        if window not in WINDOWS:
            raise ValueError(f"未知窗口: {window}")
        if by not in USER_TOP_SORTS:
            raise ValueError(f"未知排序字段: {by}")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1..100 的整数")
        now = int(now or time.time())
        win = WINDOWS[window]
        since = now - win
        interval = load_settings().collector.poll_interval_s
        # 同一用户可能在同一卡同一轮出现多个 PID；GPU·小时按用户/卡/轮次去重。
        # 不同用户共享同一卡时仍各计完整时长，是否分摊属于独立的产品口径。
        order = "gpu_hours DESC" if by == "gpu_hours" else "mem_gb_peak DESC"
        excluded = sorted(set(excluded_host_keys or ()))
        join = filt = ""
        params: list = [since, now]
        if cluster_key or excluded:
            join = ("JOIN gpu_card g ON g.id=p.gpu_id JOIN host h ON h.id=g.host_id "
                    "JOIN cluster c ON c.id=h.cluster_id")
        filters = []
        if cluster_key:    # 按集群过滤（集群视图用）
            filters.append("c.key = ?")
            params.append(cluster_key)
        if excluded:
            filters.append(f"h.key NOT IN ({','.join('?' for _ in excluded)})")
            params.extend(excluded)
        if filters:
            filt = "AND " + " AND ".join(filters)
        params.extend([interval, limit])
        sql = f"""
            WITH occupied AS (
                SELECT p.username AS username, p.gpu_id AS gpu_id, p.ts AS ts,
                       MAX(p.mem_used_mib) AS mem_used_mib
                FROM sample_proc p {join}
                WHERE p.ts >= ? AND p.ts < ? AND p.username IS NOT NULL
                      AND p.mem_used_mib > 0 {filt}
                GROUP BY p.username, p.gpu_id, p.ts
            )
            SELECT username,
                   COUNT(*) * ? / 3600.0 AS gpu_hours,
                   COUNT(DISTINCT gpu_id) AS distinct_gpus,
                   MAX(mem_used_mib)/1024.0 AS mem_gb_peak
            FROM occupied
            GROUP BY username ORDER BY {order} LIMIT ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [{"username": r["username"], "gpu_hours": round(r["gpu_hours"], 1),
                 "distinct_gpus": r["distinct_gpus"], "mem_gb_peak": round(r["mem_gb_peak"] or 0, 1)}
                for r in rows]

    def get_users_current(self, now: int | None = None,
                          freshness_s: int | None = None) -> list[dict]:
        now = int(now or time.time())
        freshness_s = freshness_s if freshness_s is not None else current_sample_max_age_s()
        snap = self.get_snapshot()
        agg: dict[str, dict] = {}
        for gpu_id, procs in snap["procs"].items():
            gpu_sample = snap["gpus"].get(gpu_id)
            if gpu_sample is None or now - gpu_sample["ts"] > freshness_s:
                continue
            for p in procs:
                if (p["mem_used_mib"] or 0) <= 0:
                    continue
                u = p["username"] or "?"
                a = agg.setdefault(u, {"username": u, "gpus": set(), "mem_mib": 0})
                a["gpus"].add(gpu_id)
                a["mem_mib"] += p["mem_used_mib"] or 0
        out = [{"username": a["username"], "distinct_gpus": len(a["gpus"]),
                "mem_gb": round(a["mem_mib"] / 1024.0, 1)} for a in agg.values()]
        out.sort(key=lambda x: x["mem_gb"], reverse=True)
        return out

    def get_users_ranking(self, window: str, now: int | None = None,
                          excluded_host_keys: Collection[str] | None = None,
                          limit: int = 200) -> dict:
        """用户占用排行：同 username 跨机器聚合，并按机器(设备)拆分 gpu_hours，
        供前端堆叠条形图（不同颜色=不同设备）。"""
        if window not in WINDOWS:
            raise ValueError(f"未知窗口: {window}")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ValueError("limit 必须是 1..1000 的整数")
        now = int(now or time.time())
        win = WINDOWS[window]
        since = now - win
        interval = load_settings().collector.poll_interval_s
        excluded = sorted(set(excluded_host_keys or ()))
        excluded_sql = ""
        excluded_params: list[str] = []
        if excluded:
            excluded_sql = f"AND h.key NOT IN ({','.join('?' for _ in excluded)})"
            excluded_params = excluded
        sql = f"""
            WITH occupied AS (
                SELECT p.username AS username, p.gpu_id AS gpu_id, p.ts AS ts,
                       h.id AS host_id, h.key AS host_key
                FROM sample_proc p
                JOIN gpu_card g ON g.id=p.gpu_id
                JOIN host h ON h.id=g.host_id
                WHERE p.ts >= ? AND p.ts < ? AND p.username IS NOT NULL
                      AND p.mem_used_mib > 0
                      {excluded_sql}
                GROUP BY p.username, p.gpu_id, p.ts, h.id, h.key
            ), by_user_host AS (
                SELECT username, host_id, host_key,
                       COUNT(*) * ? / 3600.0 AS gpu_hours
                FROM occupied
                GROUP BY username, host_id, host_key
            ), user_totals AS (
                SELECT username, SUM(gpu_hours) AS total
                FROM by_user_host
                GROUP BY username
            ), selected_users AS (
                SELECT username, total, COUNT(*) OVER() AS total_users
                FROM user_totals
                ORDER BY total DESC, username
                LIMIT ?
            )
            SELECT b.username, b.host_key, b.gpu_hours,
                   s.total, s.total_users
            FROM selected_users s
            JOIN by_user_host b ON b.username=s.username
            ORDER BY s.total DESC, s.username, b.host_key
        """
        with self.connect() as conn:
            rows = conn.execute(
                sql,
                (since, now, *excluded_params, interval, limit),
            ).fetchall()
            machine_filter = ""
            machine_params: list[str] = []
            if excluded:
                machine_filter = f"WHERE h.key NOT IN ({','.join('?' for _ in excluded)})"
                machine_params = excluded
            machines = [{"key": r["key"], "name": r["display_name"], "cluster_key": r["cluster_key"]}
                        for r in conn.execute(
                            f"""SELECT h.key, h.display_name, c.key as cluster_key
                               FROM host h LEFT JOIN cluster c ON c.id = h.cluster_id
                               {machine_filter}
                               ORDER BY h.sort_order, h.id""", machine_params)]
        users: dict[str, dict] = {}
        for r in rows:
            u = users.setdefault(r["username"],
                                 {"username": r["username"], "total": 0.0, "by_machine": {}})
            u["by_machine"][r["host_key"]] = round(r["gpu_hours"], 1)
            u["total"] += r["gpu_hours"]
        out = sorted(users.values(), key=lambda x: x["total"], reverse=True)
        for u in out:
            u["total"] = round(u["total"], 1)
        total_users = rows[0]["total_users"] if rows else 0
        return {
            "window": window,
            "machines": machines,
            "users": out,
            "total_users": total_users,
            "returned_users": len(out),
            "truncated": total_users > len(out),
            "limit": limit,
        }

    # ---- 查询：采集状态 -----------------------------------------------------
    def get_collector_status(self, online_window_s: int = 120, now: int | None = None) -> list[dict]:
        now = int(now or time.time())
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT h.key, h.display_name, h.gpu_count,
                       s.last_try_ts, s.last_ok_ts, s.gpus_seen, s.consec_fail, s.last_error
                FROM host h LEFT JOIN collector_status s ON s.host_id=h.id
                ORDER BY h.sort_order, h.id
            """).fetchall()
        out = []
        for r in rows:
            last_ok = r["last_ok_ts"]
            online = bool(last_ok and (now - last_ok) <= online_window_s)
            out.append({
                "key": r["key"], "display_name": r["display_name"],
                "gpus_expected": r["gpu_count"], "gpus_seen": r["gpus_seen"],
                "last_ok_ts": last_ok, "last_try_ts": r["last_try_ts"],
                "consec_fail": r["consec_fail"] or 0, "last_error": r["last_error"],
                "online": online,
            })
        return out
