"""配置载入 —— 定位项目根、读取并校验 inventory.yaml 与 settings.toml。

设计：所有路径相对“项目根”解析。项目根的判定优先级：
  1. 环境变量 GPUMON_ROOT
  2. 从本文件向上找含 config/inventory.yaml 的目录（开发态）
这样无论从哪运行（CLI、systemd、pytest）都能稳定定位资源。
"""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

import yaml

from .models import PALETTES, Inventory, Settings

# 代码/静态资源随 release 走；配置和数据根可由 GPUMON_ROOT 独立指定。
# 这两个根不能混用，否则 current 原子切换后 web 仍会从旧的平铺目录发静态文件。
CODE_ROOT = Path(__file__).resolve().parents[2]


def find_root() -> Path:
    env = os.environ.get("GPUMON_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "config" / "inventory.yaml").exists():
            return parent
    # 兜底：src/gpumon 的上两级
    return here.parents[2]


ROOT = find_root()


@lru_cache(maxsize=1)
def load_inventory() -> Inventory:
    path = ROOT / "config" / "inventory.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _reject_removed_fields(data)
    inv = Inventory.model_validate(data)
    _validate_unique_keys(inv)
    return inv


def _reject_removed_fields(data: object) -> None:
    """已删除的字段要显式报错，不能让 pydantic 静默忽略。

    configured_by 在 v0.3.0 removed —— 它原本会自动合成一枚"◆ XX 配置"标签。
    留着不管的话，升级后那枚标签会无声消失，用户只会觉得"网页少了个东西"。
    """
    if not isinstance(data, dict):
        return
    stale = [c.get("key", "?") for c in (data.get("clusters", []) or [])
             if isinstance(c, dict) and c.get("configured_by")]
    if not stale:
        return
    raise ValueError(
        f"集群 {stale} 还在用已移除的 configured_by。改成标签库引用：\n"
        f"  badge_library:\n"
        f"    - key: configured-by-xx\n"
        f'      text: "XX 配置"\n'
        f'      mark: "◆"\n'
        f"      tone: cyan\n"
        f'      tooltip: "由 XX 进行初始化配置"\n'
        f"  然后在这些集群下写 badges: [configured-by-xx]")


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    path = ROOT / "config" / "settings.toml"
    if not path.exists():
        raise FileNotFoundError(
            f"缺少必需配置文件: {path}。"
            "请先复制 config/settings.example.toml 为 config/settings.toml 并核对内容。"
        )
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Settings.model_validate(data)


def db_path() -> Path:
    p = Path(load_settings().db.path)
    return p if p.is_absolute() else (ROOT / p)


def _validate_badges(inv: Inventory) -> None:
    """标签库：key 必填且唯一；引用方写的 key 必须在库里查得到。

    引用错了要当场报错——静默跳过的话，网页上标签只是"不见了"，
    排查起来得翻半天配置。
    """
    seen: set[str] = set()
    for b in inv.badge_library:
        if not b.key:
            raise ValueError(f"标签库里有条目缺 key（text={b.text!r}）；库条目必须能被引用")
        if b.key in seen:
            raise ValueError(f"重复的标签 key: {b.key}")
        seen.add(b.key)

    def check(refs, where: str) -> None:
        for r in refs:
            if not isinstance(r, str) or r in seen:
                continue
            if not seen:
                raise ValueError(
                    f"{where} 引用了标签 {r!r}，但还没定义 badge_library")
            raise ValueError(
                f"{where} 引用了不存在的标签 {r!r}；标签库里有 {sorted(seen)}")

    for g in inv.capacity_groups:
        check(g.badges, f"算力域 {g.key}")
    for c in inv.clusters:
        check(c.badges, f"集群 {c.key}")


def _validate_unique_keys(inv: Inventory) -> None:
    """集群 key、主机 key 全局唯一，否则历史关联会错乱。"""
    cluster_keys, host_keys = set(), set()
    group_keys = {g.key for g in inv.capacity_groups}
    _validate_badges(inv)
    for g in inv.capacity_groups:
        if g.palette and g.palette not in PALETTES:
            raise ValueError(
                f"算力域 {g.key} 的 palette={g.palette} 不是内置色带，可选: {PALETTES}")
    for c in inv.clusters:
        if c.key in cluster_keys:
            raise ValueError(f"重复的集群 key: {c.key}")
        # 引用未声明的算力域不再是错误——resolved_groups() 会自动补一个同名域。
        # 只在明明声明了域、却拼错了 key 时提示，避免静默多出一个"孤儿域"。
        if c.capacity_group and group_keys and c.capacity_group not in group_keys:
            raise ValueError(
                f"集群 {c.key} 引用了不存在的算力域 {c.capacity_group}；"
                f"已声明的有 {sorted(group_keys)}（或留空走兜底域）")
        cluster_keys.add(c.key)
        for h in c.hosts:
            if h.key in host_keys:
                raise ValueError(f"重复的主机 key: {h.key}")
            if h.status == "active" and not h.ssh_alias:
                raise ValueError(f"active 主机 {h.key} 缺少 ssh_alias")
            host_keys.add(h.key)
