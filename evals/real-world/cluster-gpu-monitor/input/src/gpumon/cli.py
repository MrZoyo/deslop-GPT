"""命令行入口：gpumon <子命令>。

子命令：
  config-check   载入并打印 inventory + settings，校验配置
  initdb         初始化数据库（建表）
  collect        采集：--once 跑一轮后退出；否则常驻按周期轮询
  rollup-once    手动跑一次聚合 + 保留清理
  web            启动 FastAPI 网页服务

各子命令内部延迟 import，避免一个模块缺失影响其它命令。
"""
from __future__ import annotations

import argparse
import sys


def _format_localized_text(value: str | dict[str, str]) -> str:
    """CLI 没有界面语言，按配置顺序列出全部翻译。"""
    if isinstance(value, str):
        return value
    return " / ".join(f"{locale}: {text}" for locale, text in value.items())


def _cmd_config_check(args: argparse.Namespace) -> int:
    from .config import ROOT, db_path, load_inventory, load_settings

    inv = load_inventory()
    st = load_settings()
    print(f"配置/数据根: {ROOT}")
    print(f"数据库: {db_path()}")
    print(f"采集周期: {st.collector.poll_interval_s}s  并发: {st.collector.max_concurrency}")
    print(f"Web: {st.web.host}:{st.web.port}")
    print(
        "Web 查询边界: "
        f"并发 {st.web.max_query_concurrency}  "
        f"排队 {st.web.query_queue_timeout_s:g}s  "
        f"执行 {st.web.query_timeout_s:g}s  "
        f"缓存 {st.web.stats_cache_ttl_s}s  "
        f"排行 {st.web.ranking_user_limit} 人  "
        f"API 文档 {'开' if st.web.enable_docs else '关'}"
    )
    # 算力域：打印最终生效的域列表 + 每域分到的色带，配错色带名/漏声明域能立刻看出来
    groups = inv.resolved_groups()
    group_names = {g.key: g.name for g in groups}
    print("\n算力域（含自动补齐与色带分配）:")
    for g in groups:
        n_cl = sum(1 for c in inv.clusters if inv.group_key_of(c) == g.key)
        print(f"  - {g.key:12s} {g.name:12s} palette={g.palette:8s} "
              f"sort={g.sort_order:<4d} {n_cl} 集群")

    n_hosts = n_gpus = 0
    for c in sorted(inv.clusters, key=lambda x: x.sort_order):
        gk = inv.group_key_of(c)
        group_name = group_names.get(gk, gk)
        print(f"\n[{c.key}] {c.name}  ({group_name}, status={c.status})")
        if c.note:
            print(f"  note: {_format_localized_text(c.note)}")
        badges = inv.cluster_badges(c)
        if badges:
            print("  标签: " + "  ".join(
                f"[{(b.mark + ' ') if b.mark else ''}{_format_localized_text(b.text)}]"
                f"({b.tone})" for b in badges))
        if not c.hosts:
            print("  - 暂无主机")
        for _, h, gc in [(c, h, (h.gpu_count or inv.defaults.gpu_count)) for h in c.hosts]:
            alias = h.ssh_alias or "-"
            vend = f"  vendor={h.vendor}" if h.vendor else ""
            print(f"  - {h.key:18s} alias={alias:16s} {h.display_name}  "
                  f"status={h.status}  期望 {gc} 卡{vend}")
            if h.note:
                print(f"    note: {_format_localized_text(h.note)}")
            n_hosts += 1
            n_gpus += gc
    print(f"\n合计: {len(inv.clusters)} 集群 / {n_hosts} 机 / {n_gpus} 卡")
    return 0


def _cmd_initdb(args: argparse.Namespace) -> int:
    from .db.store import Store

    store = Store()
    store.init_schema()
    store.sync_topology()
    print("数据库已初始化，拓扑已同步。")
    return 0


def _cmd_collect(args: argparse.Namespace) -> int:
    from .collector.run import run_forever, run_once

    if args.once:
        return run_once(host_filter=args.host)
    run_forever()
    return 0


def _cmd_rollup_once(args: argparse.Namespace) -> int:
    from .db.rollup import Rollup
    from .db.store import Store

    Rollup(Store()).run_all()
    print("聚合与清理完成。")
    return 0


def _cmd_backup(args: argparse.Namespace) -> int:
    from .config import load_settings
    from .db.backup import backup_and_prune, list_backups

    if args.scheduled and not load_settings().backup.enabled:
        print("自动备份已在 settings.toml 中禁用，本次定时任务跳过。")
        return 0

    new_backup, deleted = backup_and_prune()  # 从配置读取 keep_count
    print(f"备份完成: {new_backup.name}  ({new_backup.stat().st_size / (1024*1024):.1f} MB)")
    if deleted:
        print(f"已删除 {len(deleted)} 个旧备份: {', '.join(f.name for f in deleted)}")

    backups = list_backups()
    print(f"\n当前备份 ({len(backups)}):")
    for b in backups:
        size_mb = b.stat().st_size / (1024 * 1024)
        print(f"  {b.name}  {size_mb:.1f} MB")
    return 0


def _cmd_web(args: argparse.Namespace) -> int:
    import uvicorn

    from .api.app import create_app
    from .config import load_settings

    st = load_settings()
    host = args.host or st.web.host
    port = args.port or st.web.port
    uvicorn.run(
        create_app(enable_docs=st.web.enable_docs),
        host=host,
        port=port,
        log_level="info",
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gpumon", description="GPU 集群占用监控")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("config-check", help="校验并打印配置").set_defaults(func=_cmd_config_check)
    sub.add_parser("initdb", help="初始化数据库").set_defaults(func=_cmd_initdb)

    c = sub.add_parser("collect", help="采集")
    c.add_argument("--once", action="store_true", help="只跑一轮后退出")
    c.add_argument("--host", default=None, help="只采指定主机 key（配合 --once 调试）")
    c.set_defaults(func=_cmd_collect)

    sub.add_parser("rollup-once", help="手动聚合+清理").set_defaults(func=_cmd_rollup_once)
    b = sub.add_parser("backup", help="备份数据库并按配置轮换")
    b.add_argument(
        "--scheduled",
        action="store_true",
        help="由 systemd timer 调用；backup.enabled=false 时跳过",
    )
    b.set_defaults(func=_cmd_backup)

    w = sub.add_parser("web", help="启动网页服务")
    w.add_argument("--host", default=None)
    w.add_argument("--port", type=int, default=None)
    w.set_defaults(func=_cmd_web)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
