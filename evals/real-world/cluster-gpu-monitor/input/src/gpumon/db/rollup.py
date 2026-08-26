"""聚合与保留清理。

三层：sample_gpu(原始~30s) → rollup_gpu_5m → rollup_gpu_1h；sample_host → rollup_host_1h。
只处理“已封口”的桶（now 已越过桶尾），用 rollup_state 水位增量推进，避免每次全表扫。
1h 表从 5m 表按 n 加权聚合（不是对均值再平均），保证与原始 AVG 一致。
"""
from __future__ import annotations

import time

from ..config import load_settings
from .store import Store


class Rollup:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    def _get_wm(self, conn, name: str) -> int:
        row = conn.execute("SELECT watermark FROM rollup_state WHERE name=?", (name,)).fetchone()
        return row[0] if row else 0

    def _set_wm(self, conn, name: str, value: int) -> None:
        conn.execute(
            "INSERT INTO rollup_state(name,watermark) VALUES(?,?) "
            "ON CONFLICT(name) DO UPDATE SET watermark=excluded.watermark", (name, value))

    def roll_gpu_5m(self, now: int) -> None:
        conn = self.store.write_conn()
        b_max = ((now - 300) // 300) * 300          # 最后一个已封口的 5m 桶起点
        if b_max < 0:
            return
        with conn:
            wm = self._get_wm(conn, "gpu_5m")
            conn.execute("""
                INSERT OR REPLACE INTO rollup_gpu_5m
                  (gpu_id,bucket_ts,n,util_gpu_avg,util_gpu_max,util_mem_avg,
                   mem_used_avg,mem_used_max,temp_avg,temp_max,power_avg)
                SELECT gpu_id,(ts/300)*300 AS b,COUNT(*),
                       AVG(util_gpu),MAX(util_gpu),AVG(util_mem),
                       AVG(mem_used_mib),MAX(mem_used_mib),AVG(temp_c),MAX(temp_c),AVG(power_w)
                FROM sample_gpu WHERE ts>=? AND ts<? GROUP BY gpu_id,b HAVING b<=?
            """, (wm, b_max + 300, b_max))
            self._set_wm(conn, "gpu_5m", b_max)

    def roll_gpu_1h(self, now: int) -> None:
        conn = self.store.write_conn()
        b_max = ((now - 3600) // 3600) * 3600
        if b_max < 0:
            return
        with conn:
            wm = self._get_wm(conn, "gpu_1h")
            conn.execute("""
                INSERT OR REPLACE INTO rollup_gpu_1h
                  (gpu_id,bucket_ts,n,util_gpu_avg,util_gpu_max,util_mem_avg,
                   mem_used_avg,mem_used_max,temp_avg,temp_max,power_avg)
                SELECT gpu_id,(bucket_ts/3600)*3600 AS b,SUM(n),
                       SUM(util_gpu_avg*n)/NULLIF(SUM(n),0),MAX(util_gpu_max),
                       SUM(util_mem_avg*n)/NULLIF(SUM(n),0),
                       SUM(mem_used_avg*n)/NULLIF(SUM(n),0),MAX(mem_used_max),
                       SUM(temp_avg*n)/NULLIF(SUM(n),0),MAX(temp_max),
                       SUM(power_avg*n)/NULLIF(SUM(n),0)
                FROM rollup_gpu_5m WHERE bucket_ts>=? AND bucket_ts<? GROUP BY gpu_id,b HAVING b<=?
            """, (wm, b_max + 3600, b_max))
            self._set_wm(conn, "gpu_1h", b_max)

    def roll_host_1h(self, now: int) -> None:
        conn = self.store.write_conn()
        b_max = ((now - 3600) // 3600) * 3600
        if b_max < 0:
            return
        with conn:
            wm = self._get_wm(conn, "host_1h")
            conn.execute("""
                INSERT OR REPLACE INTO rollup_host_1h(host_id,bucket_ts,n,cpu_util_avg,load1_avg,mem_used_avg)
                SELECT host_id,(ts/3600)*3600 AS b,COUNT(*),AVG(cpu_util_pct),AVG(load1),AVG(mem_used_mib)
                FROM sample_host WHERE ts>=? AND ts<? GROUP BY host_id,b HAVING b<=?
            """, (wm, b_max + 3600, b_max))
            self._set_wm(conn, "host_1h", b_max)

    def cleanup(self, now: int) -> None:
        ret = load_settings().retention
        raw_cut = now - ret.raw_days * 86400
        r5m_cut = now - ret.rollup_5m_days * 86400
        r1h_cut = now - ret.rollup_1h_days * 86400
        conn = self.store.write_conn()
        with conn:
            conn.execute("DELETE FROM sample_gpu WHERE ts<?", (raw_cut,))
            conn.execute("DELETE FROM sample_proc WHERE ts<?", (raw_cut,))
            conn.execute("DELETE FROM sample_host WHERE ts<?", (raw_cut,))
            conn.execute("DELETE FROM rollup_gpu_5m WHERE bucket_ts<?", (r5m_cut,))
            # 1 小时聚合此前无上限增长；按 rollup_1h_days 回收（须 > 最长时间窗）
            conn.execute("DELETE FROM rollup_gpu_1h WHERE bucket_ts<?", (r1h_cut,))
            conn.execute("DELETE FROM rollup_host_1h WHERE bucket_ts<?", (r1h_cut,))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def roll_all(self, now: int | None = None) -> None:
        now = int(now or time.time())
        self.roll_gpu_5m(now)
        self.roll_gpu_1h(now)
        self.roll_host_1h(now)

    def run_all(self, now: int | None = None) -> None:
        """聚合 + 清理（rollup-once CLI 用）。"""
        now = int(now or time.time())
        self.roll_all(now)
        self.cleanup(now)
