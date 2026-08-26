"""HTTP API 路由。所有路径在 /api 下。

设计：路由是同步 def —— FastAPI 会自动丢到线程池执行，避免阻塞事件循环；
SQLite 同步查询在线程池里跑正合适。返回 JSON，时间一律 epoch 秒。
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import time

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..config import load_inventory, load_settings
from ..db.store import WINDOWS, current_sample_max_age_s
from .deps import (
    get_store,
    mask_username,
    valid_metric,
    valid_scope,
    valid_series_id,
    valid_user_sort,
    valid_window,
)
from .query_control import bounded_query

router = APIRouter(prefix="/api")

# 繁忙阈值：瞬时利用率 ≥ 该值视为“在用”
BUSY_THRESHOLD = 10

_TOPOLOGY_CLUSTER_FIELDS = (
    "id", "key", "name", "sort_order", "capacity_group",
    "capacity_group_name", "capacity_group_sort", "status", "note", "note_i18n", "badges",
)
_TOPOLOGY_HOST_FIELDS = (
    "id", "cluster_id", "key", "display_name", "gpu_count", "sort_order",
    "status", "note", "note_i18n", "vendor", "meta",
)
_TOPOLOGY_GPU_FIELDS = (
    "id", "host_id", "gpu_index", "name", "mem_total_mib",
)


def _localized_api_fields(name: str, value: str | dict[str, str] | None) -> dict:
    """同时下发旧字符串字段和完整翻译，兼容部署前仍打开的浏览器标签页。

    旧前端会把 ``text``/``note`` 直接交给 DOM，只能接收字符串；新前端优先读取
    ``*_i18n``。映射的第一条翻译就是配置约定的最终回退值。
    """
    if isinstance(value, dict):
        fallback = next(iter(value.values()), "")
        return {name: fallback, f"{name}_i18n": value}
    return {name: value, f"{name}_i18n": None}


def _badge_api_payload(badge) -> dict:
    payload = badge.model_dump()
    payload.update(_localized_api_fields("text", badge.text))
    payload.update(_localized_api_fields("tooltip", badge.tooltip))
    return payload


def _inventory_ui_meta() -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """Inventory 中只服务 UI 的分组/状态元数据，不进入 DB schema。"""
    inv = load_inventory()
    # resolved_groups() 已经补齐未声明的域、兜底域，并分配好 palette，这里只做序列化。
    groups = {
        g.key: {
            "key": g.key,
            "name": g.name,
            "sort_order": g.sort_order,
            **_localized_api_fields("description", g.description),
            "palette": g.palette,
            "badges": [_badge_api_payload(b) for b in inv.group_badges(g)],
        }
        for g in inv.resolved_groups()
    }
    clusters = {}
    hosts = {}
    for c in inv.clusters:
        gk = inv.group_key_of(c)
        clusters[c.key] = {
            "capacity_group": gk,
            "capacity_group_name": groups[gk]["name"],
            "capacity_group_sort": groups[gk]["sort_order"],
            "status": c.status,
            **_localized_api_fields("note", c.note),
            "badges": [_badge_api_payload(b) for b in inv.cluster_badges(c)],
        }
        for h in c.hosts:
            hosts[h.key] = {
                "status": h.status,
                **_localized_api_fields("note", h.note),
                "vendor": h.vendor,
                "meta": h.meta,
            }
    groups_out = sorted(groups.values(), key=lambda g: (g["sort_order"], g["key"]))
    return groups_out, clusters, hosts


def _orphan_cluster_meta() -> dict:
    """DB 里有、inventory 里已没有的集群（手工删过条目）的兜底元数据。

    不能写死机构名——落到 defaults 的兜底域，与 resolved_groups() 补出的那个域一致，
    这样它在网页上会和其它"未分组"集群归到同一堆，而不是凭空多出一个域。
    """
    inv = load_inventory()
    return {
        "capacity_group": inv.defaults.fallback_group_key,
        "capacity_group_name": inv.defaults.fallback_group_name,
        "capacity_group_sort": 999,
        "status": "active",
        "note": None,
        "note_i18n": None,
        "badges": [],
    }


def _host_placeholder(cluster_id: int | None, h, gpu_count: int) -> dict:
    return {
        "id": None,
        "cluster_id": cluster_id,
        "key": h.key,
        "display_name": h.display_name,
        "gpu_count": gpu_count,
        "sort_order": 0,
        "gpus": [],
    }


def _drop_retired(topo: list[dict], cluster_meta: dict[str, dict],
                  host_meta: dict[str, dict]) -> list[dict]:
    """滤掉 status=retired 的主机/集群，让退役机器从网页消失（DB 行仍在，历史保留）。
    退役主机所在集群若因此变空，则整簇一并隐藏；本就为空的集群不受影响。"""
    out = []
    for c in topo:
        if (cluster_meta.get(c["key"]) or {}).get("status") == "retired":
            continue
        kept_hosts = [h for h in c["hosts"]
                      if (host_meta.get(h["key"]) or {}).get("status") != "retired"]
        # 集群原本有主机、但全被退役滤空 → 整簇隐藏；原本就空的集群（无该情况）保留
        if c["hosts"] and not kept_hosts:
            continue
        out.append({**c, "hosts": kept_hosts})
    return out


def _retired_inventory_host_keys() -> set[str]:
    """集群或主机任一层标 retired，都视为该主机已退役。"""
    inv = load_inventory()
    return {
        host.key
        for cluster in inv.clusters
        for host in cluster.hosts
        if cluster.status == "retired" or host.status == "retired"
    }


def _cache_as_of(now: int | None = None) -> int | None:
    ttl = load_settings().web.stats_cache_ttl_s
    if ttl == 0:
        return None
    current = int(now or time.time())
    return current - current % ttl


@lru_cache(maxsize=64)
def _cached_avg(store, window: str, scope: str, metric: str, as_of: int):
    return store.get_avg(window, scope, metric, now=as_of)


@lru_cache(maxsize=32)
def _cached_avg_multi(store, scope: str, metric: str, as_of: int):
    return store.get_avg_multi(scope, metric, now=as_of)


@lru_cache(maxsize=128)
def _cached_series(store, scope: str, entity_id: int | None, metric: str,
                   window: str, as_of: int):
    return store.get_series(scope, entity_id, metric, window, now=as_of)


@lru_cache(maxsize=64)
def _cached_users_top(store, window: str, by: str, limit: int,
                      cluster_key: str | None, excluded: tuple[str, ...], as_of: int):
    return store.get_users_top(
        window,
        by=by,
        limit=limit,
        cluster_key=cluster_key,
        excluded_host_keys=excluded,
        now=as_of,
    )


@lru_cache(maxsize=32)
def _cached_users_ranking(store, window: str, excluded: tuple[str, ...],
                          limit: int, as_of: int):
    return store.get_users_ranking(
        window,
        excluded_host_keys=excluded,
        limit=limit,
        now=as_of,
    )


def _get_avg(store, window: str, scope: str, metric: str, now: int | None = None):
    as_of = _cache_as_of(now)
    if as_of is None:
        return store.get_avg(window, scope, metric, now=now)
    return _cached_avg(store, window, scope, metric, as_of)


def _get_avg_multi(store, scope: str, metric: str):
    as_of = _cache_as_of()
    if as_of is None:
        return store.get_avg_multi(scope, metric)
    return _cached_avg_multi(store, scope, metric, as_of)


def _get_series(store, scope: str, entity_id: int | None,
                metric: str, window: str):
    as_of = _cache_as_of()
    if as_of is None:
        return store.get_series(scope, entity_id, metric, window)
    return _cached_series(store, scope, entity_id, metric, window, as_of)


def _get_users_top(store, window: str, by: str, limit: int,
                   cluster_key: str | None, excluded: tuple[str, ...]):
    as_of = _cache_as_of()
    if as_of is None:
        return store.get_users_top(
            window,
            by=by,
            limit=limit,
            cluster_key=cluster_key,
            excluded_host_keys=excluded,
        )
    return deepcopy(
        _cached_users_top(store, window, by, limit, cluster_key, excluded, as_of)
    )


def _get_users_ranking(store, window: str, excluded: tuple[str, ...], limit: int):
    as_of = _cache_as_of()
    if as_of is None:
        return store.get_users_ranking(
            window,
            excluded_host_keys=excluded,
            limit=limit,
        )
    return deepcopy(_cached_users_ranking(store, window, excluded, limit, as_of))


def _clear_stats_caches_for_tests() -> None:
    for cached in (
        _cached_avg,
        _cached_avg_multi,
        _cached_series,
        _cached_users_top,
        _cached_users_ranking,
    ):
        cached.cache_clear()


def _topology_with_inventory_placeholders() -> tuple[list[dict], list[dict], dict[str, dict], dict[str, dict]]:
    """DB 拓扑 + inventory 中尚未同步的空集群占位。retired 的主机/集群不下发。"""
    store_topo = get_store().get_topology()
    inv = load_inventory()
    groups, cluster_meta, host_meta = _inventory_ui_meta()
    existing = {c["key"]: c for c in store_topo}
    for c in load_inventory().clusters:
        if c.key in existing:
            db_cluster = existing[c.key]
            existing_hosts = {h["key"] for h in db_cluster["hosts"]}
            for i, h in enumerate(c.hosts):
                if h.key in existing_hosts:
                    continue
                ph = _host_placeholder(db_cluster["id"], h, h.gpu_count or inv.defaults.gpu_count)
                ph["sort_order"] = i
                db_cluster["hosts"].append(ph)
            db_cluster["hosts"].sort(key=lambda h: (h.get("sort_order") or 0, h["key"]))
            continue
        hosts = []
        for i, h in enumerate(c.hosts):
            ph = _host_placeholder(None, h, h.gpu_count or inv.defaults.gpu_count)
            ph["sort_order"] = i
            hosts.append(ph)
        store_topo.append({
            "id": None,
            "key": c.key,
            "name": c.name,
            "sort_order": c.sort_order,
            "hosts": hosts,
        })
    store_topo.sort(key=lambda c: (c.get("sort_order") or 0, c["key"]))
    store_topo = _drop_retired(store_topo, cluster_meta, host_meta)
    return store_topo, groups, cluster_meta, host_meta


def _selected_fields(item: dict, fields: tuple[str, ...]) -> dict:
    return {field: item[field] for field in fields if field in item}


def _public_topology(topo: list[dict]) -> list[dict]:
    """只下发 UI/公开 API 需要的字段，不暴露 SSH alias 和硬件 UUID。"""
    clusters = []
    for cluster in topo:
        public_cluster = _selected_fields(cluster, _TOPOLOGY_CLUSTER_FIELDS)
        public_hosts = []
        for host in cluster.get("hosts", []):
            public_host = _selected_fields(host, _TOPOLOGY_HOST_FIELDS)
            public_host["gpus"] = [
                _selected_fields(gpu, _TOPOLOGY_GPU_FIELDS)
                for gpu in host.get("gpus", [])
            ]
            public_hosts.append(public_host)
        public_cluster["hosts"] = public_hosts
        clusters.append(public_cluster)
    return clusters


@router.get("/meta")
def meta():
    """前端启动时拉一次：可用窗口、服务器时间、是否打码、采集周期。"""
    st = load_settings()
    groups, _, _ = _inventory_ui_meta()
    return {
        "windows": list(WINDOWS),
        "server_time": int(time.time()),
        "mask_users": st.privacy.mask_users,
        "poll_interval_s": st.collector.poll_interval_s,
        "busy_threshold": BUSY_THRESHOLD,
        "capacity_groups": groups,
    }


@router.get("/topology")
def topology():
    topo, groups, cluster_meta, host_meta = _topology_with_inventory_placeholders()
    for c in topo:
        c.update(cluster_meta.get(c["key"], _orphan_cluster_meta()))
        for h in c["hosts"]:
            h.update(host_meta.get(h["key"],
                                   {"status": "active", "note": None, "note_i18n": None,
                                    "vendor": None, "meta": {}}))
    return {"capacity_groups": groups, "clusters": _public_topology(topo)}


@router.get("/overview")
@bounded_query
def overview(window: str = Query("24h")):
    """总览页一把拿全：集群→机→卡（瞬时 + 该窗均值 + coverage + 使用人），加全局汇总。"""
    window = valid_window(window)
    store = get_store()
    now = int(time.time())
    topo, groups, cluster_meta, host_meta = _topology_with_inventory_placeholders()
    snap = store.get_snapshot()
    avg_list = _get_avg(store, window, "gpu", "util_gpu", now=now)
    avg_by_gpu = {a["gpu_id"]: a for a in avg_list}
    recent_by_gpu = store.get_util_recent(now=now)   # 卡片大字/底色用的近期(10min)平滑值
    status_by_host = {s["key"]: s for s in store.get_collector_status(now=now)}
    sample_max_age_s = current_sample_max_age_s()

    util_now_vals, util_avg_vals = [], []
    cards_total = cards_busy = 0
    clusters_out = []
    for c in topo:
        hosts_out = []
        for h in c["hosts"]:
            h_meta = host_meta.get(h["key"], {
                "status": "active", "note": None, "note_i18n": None, "meta": {},
            })
            st = status_by_host.get(h["key"], {})
            host_online = st.get("online", False)
            sys_row = snap["hosts"].get(h["id"])
            gpus_out = []
            for g in h["gpus"]:
                gid = g["id"]
                # 主机离线时，快照里的最后一条样本已陈旧，不能当作实时值下发。
                # 否则会误导"卡还在被占用"，并污染下面的当前均值/满载数/热点榜。
                now_row = snap["gpus"].get(gid) if host_online else None
                if now_row and now - now_row["ts"] > sample_max_age_s:
                    now_row = None
                util_now = now_row["util_gpu"] if now_row else None
                # 近期(10min)平滑值：卡片大字/底色的实际显示值；离线同 now 一样置空。
                util_recent = recent_by_gpu.get(gid) if now_row else None
                a = avg_by_gpu.get(gid, {})
                # 使用人同样来自快照，离线时一并置空，避免离线卡仍显示"使用人"。
                # 只保留真正占用了显存的进程：used_memory 为 N/A(None) 或 <=0 的进程
                # 不算"使用人"（只是挂了个进程但没占卡）。
                users = [
                    {"username": mask_username(p["username"]), "comm": p["comm"],
                     "mem_used_mib": p["mem_used_mib"]}
                    for p in (snap["procs"].get(gid, []) if now_row else [])
                    if (p["mem_used_mib"] or 0) > 0
                ]
                cards_total += 1
                if util_now is not None:
                    util_now_vals.append(util_now)      # 瞬时利用率 KPI 仍取真瞬时（全队列均值，抖动自然被摊平）
                # 在用/满载按近期平滑值判定，与卡片大字/底色一致，避免瞬时抖动误判。
                if util_recent is not None and util_recent >= BUSY_THRESHOLD:
                    cards_busy += 1
                if a.get("avg") is not None:
                    util_avg_vals.append(a["avg"])
                gpus_out.append({
                    "gpu_id": gid, "index": g["gpu_index"], "name": g["name"],
                    "mem_total_mib": g["mem_total_mib"],
                    "now": None if not now_row else {
                        "util_gpu": now_row["util_gpu"], "util_mem": now_row["util_mem"],
                        "mem_used_mib": now_row["mem_used_mib"], "temp_c": now_row["temp_c"],
                        "power_w": now_row["power_w"], "ts": now_row["ts"]},
                    "util_recent": util_recent,
                    "avg": a.get("avg"), "coverage": a.get("coverage"),
                    "users": users,
                })
            hosts_out.append({
                "id": h["id"],
                "key": h["key"], "display_name": h["display_name"],
                "status": h_meta["status"], "note": h_meta["note"],
                "note_i18n": h_meta["note_i18n"], "meta": h_meta["meta"],
                "gpu_count": h["gpu_count"], "online": st.get("online", False),
                "gpus_seen": st.get("gpus_seen"), "consec_fail": st.get("consec_fail", 0),
                "last_error": st.get("last_error"),
                "system": None if not sys_row else {
                    "ncpu": sys_row["ncpu"], "cpu_util_pct": sys_row["cpu_util_pct"],
                    "load1": sys_row["load1"], "load5": sys_row["load5"], "load15": sys_row["load15"],
                    "mem_used_mib": sys_row["mem_used_mib"], "mem_total_mib": sys_row["mem_total_mib"],
                    "ts": sys_row["ts"]},
                "gpus": gpus_out,
            })
        meta = cluster_meta.get(c["key"], _orphan_cluster_meta())
        clusters_out.append({"id": c["id"], "key": c["key"], "name": c["name"],
                             "sort_order": c["sort_order"], **meta, "hosts": hosts_out})

    active_host_keys = {
        h["key"]
        for c in topo
        for h in c["hosts"]
        if host_meta.get(h["key"], {"status": "active"})["status"] == "active"
    }
    hosts_online = sum(1 for key, s in status_by_host.items()
                       if key in active_host_keys and s.get("online"))
    hosts_total = len(active_host_keys)
    hosts_planned = sum(1 for c in topo for h in c["hosts"]
                        if host_meta.get(h["key"], {"status": "active"})["status"] != "active")
    cards_expected = sum(h["gpu_count"] for c in topo for h in c["hosts"])
    summary = {
        "window": window, "cards_total": cards_total, "cards_busy": cards_busy,
        "cards_idle": cards_total - cards_busy,
        "cards_expected": cards_expected,
        "util_now_avg": round(sum(util_now_vals) / len(util_now_vals), 1) if util_now_vals else None,
        "util_avg": round(sum(util_avg_vals) / len(util_avg_vals), 1) if util_avg_vals else None,
        "hosts_online": hosts_online, "hosts_total": hosts_total,
        "hosts_planned": hosts_planned,
    }
    return {"now": now, "window": window, "capacity_groups": groups,
            "clusters": clusters_out, "summary": summary}


@router.get("/metrics/avg")
@bounded_query
def metrics_avg(window: str = Query("24h"),
                scope: str = Query("gpu"),
                metric: str = Query("util_gpu")):
    window = valid_window(window)
    scope = valid_scope(scope)
    metric = valid_metric(metric)
    store = get_store()
    return {"window": window, "scope": scope, "metric": metric,
            "items": _get_avg(store, window, scope, metric)}


@router.get("/metrics/avg_multi")
@bounded_query
def metrics_avg_multi(scope: str = Query("host"),
                      metric: str = Query("util_gpu")):
    scope = valid_scope(scope)
    metric = valid_metric(metric)
    store = get_store()
    return {"scope": scope, "metric": metric,
            "windows": _get_avg_multi(store, scope, metric)}


@router.get("/metrics/series")
@bounded_query
def metrics_series(scope: str = Query("gpu"),
                   id: int | None = Query(None, ge=1),
                   metric: str = Query("util_gpu"),
                   window: str = Query("24h")):
    window = valid_window(window)
    scope = valid_scope(scope)
    metric = valid_metric(metric)
    id = valid_series_id(scope, id)
    store = get_store()
    return {"scope": scope, "id": id, "metric": metric, "window": window,
            "points": _get_series(store, scope, id, metric, window)}


@router.get("/users/top")
@bounded_query
def users_top(window: str = Query("24h"),
              by: str = Query("gpu_hours"),
              limit: int = Query(20, ge=1, le=100),
              cluster: str | None = Query(None)):
    window = valid_window(window)
    by = valid_user_sort(by)
    excluded = tuple(sorted(_retired_inventory_host_keys()))
    items = _get_users_top(
        get_store(), window, by, limit, cluster, excluded,
    )
    for it in items:
        it["username"] = mask_username(it["username"])
    return {"window": window, "by": by, "cluster": cluster, "items": items}


@router.get("/users/ranking")
@bounded_query
def users_ranking(window: str = Query("24h")):
    """全局用户占用排行：同 username 跨设备聚合，按设备拆分 gpu_hours（堆叠条用）。
    退役机器(status=retired)彻底移除，其 GPU·h 不计入合计。"""
    window = valid_window(window)
    retired = _retired_inventory_host_keys()
    limit = load_settings().web.ranking_user_limit
    data = _get_users_ranking(
        get_store(), window, tuple(sorted(retired)), limit
    )

    # 过滤 retired 机器，并补充 capacity_group
    _, cluster_meta, _ = _inventory_ui_meta()
    data["machines"] = [
        {**m, "capacity_group": cluster_meta.get(m["cluster_key"], {}).get("capacity_group")}
        for m in data["machines"]
        if m["key"] not in retired
    ]

    # 过滤每个用户的 by_machine，重算 total
    for u in data["users"]:
        u["by_machine"] = {k: v for k, v in u["by_machine"].items() if k not in retired}
        u["total"] = round(sum(u["by_machine"].values()), 1)
        u["username"] = mask_username(u["username"])

    # 移除 total=0 的用户（所有使用量都在退役机器上）
    data["users"] = [u for u in data["users"] if u["total"] > 0]

    return data


@router.get("/users/current")
def users_current():
    items = get_store().get_users_current()
    for it in items:
        it["username"] = mask_username(it["username"])
    return {"items": items}


@router.get("/health")
def health():
    try:
        # readiness 必须覆盖所有 UI 路由依赖的配置；只验证 DB 会让缺配置的新进程
        # 错误地通过健康检查，随后其它接口才 500。
        load_settings()
        load_inventory()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "status": "unavailable", "error": "configuration unavailable"},
        )

    try:
        store = get_store()
        with store.connect() as conn:
            row = conn.execute("SELECT MAX(ts) FROM sample_gpu").fetchone()
        last = row[0] if row else None
        age = (int(time.time()) - last) if last else None
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "status": "unavailable", "error": "database unavailable"},
        )

    stale_after = current_sample_max_age_s()
    stale = age is None or age > stale_after
    return {
        "ok": not stale,
        "status": "stale" if stale else "ok",
        "last_sample_ts": last,
        "last_sample_age_s": age,
        "stale_after_s": stale_after,
    }


@router.get("/live")
def live():
    """纯进程 liveness：不读配置和数据库。"""
    return {"ok": True, "status": "alive"}


@router.get("/collector/status")
def collector_status():
    _, _, host_meta = _inventory_ui_meta()
    hosts = get_store().get_collector_status()
    known = {h["key"] for h in hosts}
    for h in hosts:
        meta = host_meta.get(h["key"], {
            "status": "active", "note": None, "note_i18n": None, "meta": {},
        })
        h.update(meta)
    inv = load_inventory()
    for c in inv.clusters:
        for h in c.hosts:
            if h.key in known:
                continue
            hosts.append({
                "key": h.key,
                "display_name": h.display_name,
                "gpus_expected": h.gpu_count or inv.defaults.gpu_count,
                "gpus_seen": None,
                "last_ok_ts": None,
                "last_try_ts": None,
                "consec_fail": 0,
                "last_error": None,
                "online": False,
                "status": h.status,
                **_localized_api_fields("note", h.note),
                "meta": h.meta,
            })
    hosts = [h for h in hosts if h.get("status") != "retired"]  # 退役机器不进健康灯/状态列表
    return {"hosts": hosts}
