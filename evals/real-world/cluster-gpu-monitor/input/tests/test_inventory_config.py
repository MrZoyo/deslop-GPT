"""配置层的自适应能力：任意命名、算力域自动补齐、色带轮转、自定义标签。

这些用例的意义：只要按 算力域→集群→服务器 三层填清单，不管名字叫什么、
声明了几个域，后端都要给出完整且不含硬编码机构名的元数据。
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from gpumon.models import (
    PALETTES,
    BadgeCfg,
    CapacityGroupCfg,
    ClusterCfg,
    Defaults,
    HostCfg,
    Inventory,
    Settings,
)


def _host(key: str) -> HostCfg:
    return HostCfg(key=key, ssh_alias=f"alias-{key}", display_name=key.upper())


def test_group_declared_explicitly_keeps_name_and_palette():
    inv = Inventory(
        capacity_groups=[CapacityGroupCfg(key="lab", name="实验室算力", sort_order=1,
                                          palette="violet")],
        clusters=[ClusterCfg(key="c1", name="集群一", capacity_group="lab", hosts=[_host("h1")])],
    )
    groups = inv.resolved_groups()
    assert [g.key for g in groups] == ["lab"]
    assert groups[0].name == "实验室算力"
    assert groups[0].palette == "violet"
    assert inv.group_key_of(inv.clusters[0]) == "lab"


def test_cluster_without_group_falls_back_to_neutral_domain():
    """没写 capacity_group：落到兜底域，名字取 defaults，不出现任何机构名。"""
    inv = Inventory(clusters=[ClusterCfg(key="c1", name="集群一", hosts=[_host("h1")])])
    groups = inv.resolved_groups()
    assert [g.key for g in groups] == ["default"]
    assert groups[0].name == "未分组"
    assert groups[0].palette  # 兜底域也分到了色带


def test_fallback_domain_name_is_configurable():
    inv = Inventory(
        defaults=Defaults(fallback_group_key="misc", fallback_group_name="Other Capacity"),
        clusters=[ClusterCfg(key="c1", name="c1", hosts=[_host("h1")])],
    )
    groups = inv.resolved_groups()
    assert [(g.key, g.name) for g in groups] == [("misc", "Other Capacity")]


def test_palette_auto_rotates_and_never_repeats_within_builtin_range():
    """8 个域各拿到不同的内置色带——旧版第 3 个域起会全掉进灰色。"""
    inv = Inventory(
        capacity_groups=[CapacityGroupCfg(key=f"g{i}", name=f"域{i}", sort_order=i)
                         for i in range(8)],
        clusters=[ClusterCfg(key="c1", name="c1", capacity_group="g0", hosts=[_host("h1")])],
    )
    palettes = [g.palette for g in inv.resolved_groups()]
    assert len(set(palettes)) == 8
    assert set(palettes) == set(PALETTES)


def test_more_domains_than_builtin_palettes_still_resolves():
    """12 个域：内置 8 条用尽后仍要每个域都有 palette（前端会按域名生成新色相）。"""
    inv = Inventory(
        capacity_groups=[CapacityGroupCfg(key=f"g{i}", name=f"域{i}", sort_order=i)
                         for i in range(12)],
        clusters=[ClusterCfg(key="c1", name="c1", capacity_group="g0", hosts=[_host("h1")])],
    )
    groups = inv.resolved_groups()
    assert len(groups) == 12
    assert all(g.palette for g in groups)


def test_inline_badges_keep_declared_order():
    """内联标签按声明顺序原样输出，字段不被改写。"""
    c = ClusterCfg(key="c1", name="c1",
                   badges=[BadgeCfg(text="ROCm", tone="gold", mark="◆"),
                           BadgeCfg(text="IB", tone="green")])
    badges = c.resolved_badges()
    assert [b.text for b in badges] == ["ROCm", "IB"]
    assert badges[0].mark == "◆"
    assert badges[0].tone == "gold"


def test_localized_badge_and_notes_keep_translation_order():
    """语言映射原样保序，API 才能按第一条已配置翻译回退。"""
    text = {"zh": "自建", "en": "Self-built"}
    detail = {"en": "Built here", "fr": "Construit ici"}
    badge = BadgeCfg(text=text, tooltip=detail)
    group = CapacityGroupCfg(key="g", name="G", description=detail)
    host = HostCfg(key="h", ssh_alias="h", display_name="H", note=text)
    cluster = ClusterCfg(key="c", name="C", note=detail, hosts=[host])

    assert badge.text == text
    assert list(badge.model_dump()["text"]) == ["zh", "en"]
    assert badge.tooltip == detail
    assert group.description == detail
    assert cluster.note == detail
    assert cluster.hosts[0].note == text


def test_one_translation_is_valid():
    badge = BadgeCfg(text={"en": "Only translation"}, tooltip={"zh": "唯一说明"})

    assert badge.text == {"en": "Only translation"}
    assert badge.tooltip == {"zh": "唯一说明"}


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"zh": ""},
        {"zh_CN": "中文"},
        {"zh": "x" * 129},
    ],
)
def test_invalid_localized_badge_text_is_rejected(value):
    with pytest.raises(ValidationError):
        BadgeCfg(text=value)


def test_localized_notes_reject_empty_or_oversized_translations():
    with pytest.raises(ValidationError):
        CapacityGroupCfg(key="g", name="G", description={})
    with pytest.raises(ValidationError):
        ClusterCfg(key="c", name="C", note={"en": "x" * 2049})


def test_no_badges_yields_empty_list():
    assert ClusterCfg(key="c1", name="c1").resolved_badges() == []


# ---------------------------------------------------------------------------
# 标签库：一处定义、多处引用。改库里的文案，所有引用处一起变 —— 这是该功能的重点。
# ---------------------------------------------------------------------------
def _inv_with_library(**kw) -> Inventory:
    return Inventory(
        badge_library=[
            BadgeCfg(key="self-built", text="自建", mark="◆", tone="cyan",
                     tooltip="自己装的机"),
            BadgeCfg(key="liquid", text="液冷", tone="violet"),
        ],
        **kw,
    )


def test_cluster_badge_reference_expands_from_library():
    inv = _inv_with_library(
        clusters=[ClusterCfg(key="c1", name="c1", badges=["self-built", "liquid"],
                             hosts=[_host("h1")])],
    )
    badges = inv.cluster_badges(inv.clusters[0])
    assert [b.text for b in badges] == ["自建", "液冷"]
    assert badges[0].mark == "◆"
    assert badges[0].tooltip == "自己装的机"


def test_same_badge_reused_across_domain_and_cluster():
    """同一枚标签挂到算力域和集群上，两边拿到的是同一份定义。"""
    inv = _inv_with_library(
        capacity_groups=[CapacityGroupCfg(key="g", name="G", badges=["self-built"])],
        clusters=[ClusterCfg(key="c1", name="c1", capacity_group="g",
                             badges=["self-built"], hosts=[_host("h1")])],
    )
    from_group = inv.group_badges(inv.capacity_groups[0])
    from_cluster = inv.cluster_badges(inv.clusters[0])
    assert [b.text for b in from_group] == ["自建"]
    assert from_group[0].model_dump() == from_cluster[0].model_dump()


def test_library_reference_and_inline_can_mix():
    """库引用与内联混写时，顺序按声明顺序，不因来源不同而重排。"""
    inv = _inv_with_library(
        clusters=[ClusterCfg(key="c1", name="c1",
                             badges=[BadgeCfg(text="ROCm", tone="gold"),
                                     "self-built", "liquid"],
                             hosts=[_host("h1")])],
    )
    assert [b.text for b in inv.cluster_badges(inv.clusters[0])] == \
        ["ROCm", "自建", "液冷"]


def test_configured_by_is_rejected_by_model():
    """即使绕过 YAML 专用迁移提示，模型本身也不能吞掉旧字段。"""
    with pytest.raises(ValidationError, match="configured_by"):
        ClusterCfg.model_validate({"key": "c1", "name": "c1", "configured_by": "运维组"})


def test_stale_configured_by_in_yaml_is_rejected():
    """老配置直接跑要报错并给出迁移写法，不能让那枚标签无声消失。"""
    from gpumon.config import _reject_removed_fields

    data = {"clusters": [{"key": "c1", "name": "c1", "configured_by": "运维组"}]}
    with pytest.raises(ValueError, match="已移除的 configured_by"):
        _reject_removed_fields(data)


def test_clean_yaml_passes_removed_field_check():
    from gpumon.config import _reject_removed_fields

    _reject_removed_fields({"clusters": [{"key": "c1", "badges": ["x"]}]})
    _reject_removed_fields({})
    _reject_removed_fields({"clusters": None})


def test_unknown_badge_reference_rejected():
    """引用打错字要当场报错——静默跳过的话标签只是'不见了'，很难查。"""
    from gpumon.config import _validate_unique_keys

    inv = _inv_with_library(
        clusters=[ClusterCfg(key="c1", name="c1", badges=["liqiud"], hosts=[_host("h1")])],
    )
    with pytest.raises(ValueError, match="不存在的标签"):
        _validate_unique_keys(inv)


def test_domain_badge_reference_also_validated():
    from gpumon.config import _validate_unique_keys

    inv = _inv_with_library(
        capacity_groups=[CapacityGroupCfg(key="g", name="G", badges=["nope"])],
        clusters=[ClusterCfg(key="c1", name="c1", capacity_group="g", hosts=[_host("h1")])],
    )
    with pytest.raises(ValueError, match="不存在的标签"):
        _validate_unique_keys(inv)


def test_library_entry_without_key_rejected():
    from gpumon.config import _validate_unique_keys

    inv = Inventory(
        badge_library=[BadgeCfg(text="没 key 的标签")],
        clusters=[ClusterCfg(key="c1", name="c1", hosts=[_host("h1")])],
    )
    with pytest.raises(ValueError, match="缺 key"):
        _validate_unique_keys(inv)


def test_duplicate_library_key_rejected():
    from gpumon.config import _validate_unique_keys

    inv = Inventory(
        badge_library=[BadgeCfg(key="dup", text="一"), BadgeCfg(key="dup", text="二")],
        clusters=[ClusterCfg(key="c1", name="c1", hosts=[_host("h1")])],
    )
    with pytest.raises(ValueError, match="重复的标签 key"):
        _validate_unique_keys(inv)


def test_unknown_palette_rejected():
    with pytest.raises(ValidationError, match="palette"):
        CapacityGroupCfg(key="g", name="g", palette="chartreuse")


def test_typo_in_declared_group_still_rejected():
    """声明了域却把 key 拼错 → 报错，而不是静默多出一个孤儿域。"""
    from gpumon.config import _validate_unique_keys

    inv = Inventory(
        capacity_groups=[CapacityGroupCfg(key="lab", name="lab")],
        clusters=[ClusterCfg(key="c1", name="c1", capacity_group="labb", hosts=[_host("h1")])],
    )
    with pytest.raises(ValueError, match="不存在的算力域"):
        _validate_unique_keys(inv)


# ---------------------------------------------------------------------------
# 严格配置边界：拼写错误、危险 SSH 位置参数和无意义数值必须在启动前失败。
# ---------------------------------------------------------------------------
def test_unknown_nested_config_field_is_rejected():
    with pytest.raises(ValidationError, match="poll_intervl_s"):
        Settings.model_validate({"collector": {"poll_intervl_s": 30}})

    with pytest.raises(ValidationError, match="unexpected"):
        Inventory.model_validate({
            "clusters": [{
                "key": "c1",
                "name": "c1",
                "hosts": [{
                    "key": "h1",
                    "ssh_alias": "host-1",
                    "display_name": "H1",
                    "unexpected": True,
                }],
            }],
        })


@pytest.mark.parametrize(
    "data",
    [
        {"collector": {"poll_interval_s": 0}},
        {"collector": {"max_concurrency": 0}},
        {"retention": {"raw_days": 30}},
        {"web": {"port": 70_000}},
        {"web": {"max_query_concurrency": 0}},
        {"web": {"query_queue_timeout_s": -1}},
        {"web": {"query_timeout_s": 0}},
        {"web": {"stats_cache_ttl_s": 301}},
        {"web": {"ranking_user_limit": 0}},
        {"backup": {"keep_count": 0}},
        {"backup": {"hour": 99}},
    ],
)
def test_invalid_settings_ranges_are_rejected(data):
    with pytest.raises(ValidationError):
        Settings.model_validate(data)


def test_collector_rejects_excessive_combined_ssh_output_budget():
    with pytest.raises(ValidationError, match="不能超过 64 MiB"):
        Settings.model_validate({
            "collector": {
                "max_concurrency": 8,
                "ssh_output_limit_bytes": 16 * 1024 * 1024,
            }
        })

    accepted = Settings.model_validate({
        "collector": {
            "max_concurrency": 4,
            "ssh_output_limit_bytes": 16 * 1024 * 1024,
        }
    })
    assert accepted.collector.ssh_output_limit_bytes == 16 * 1024 * 1024


def test_inventory_enums_and_identifiers_are_strict():
    with pytest.raises(ValidationError, match="ssh_alias"):
        HostCfg(key="h1", ssh_alias="-oProxyCommand=bad", display_name="H1")
    with pytest.raises(ValidationError, match="key"):
        HostCfg(key="", ssh_alias="host-1", display_name="H1")
    with pytest.raises(ValidationError, match="gpu_count"):
        HostCfg(key="h1", ssh_alias="host-1", display_name="H1", gpu_count=-1)
    with pytest.raises(ValidationError, match="status"):
        HostCfg(key="h1", ssh_alias="host-1", display_name="H1", status="online")
    with pytest.raises(ValidationError, match="vendor"):
        HostCfg(key="h1", ssh_alias="host-1", display_name="H1", vendor="intel")
    with pytest.raises(ValidationError, match="tone"):
        BadgeCfg(text="bad", tone="red")


def test_public_example_configs_pass_strict_models():
    root = Path(__file__).resolve().parents[1]
    inventory_data = yaml.safe_load(
        (root / "config" / "inventory.example.yaml").read_text(encoding="utf-8")
    )
    settings_data = tomllib.loads(
        (root / "config" / "settings.example.toml").read_text(encoding="utf-8")
    )

    inv = Inventory.model_validate(inventory_data)
    Settings.model_validate(settings_data)
    from gpumon.config import _validate_unique_keys
    _validate_unique_keys(inv)


def test_retention_default_covers_full_month_with_headroom():
    settings = Settings.model_validate({})
    assert settings.retention.raw_days == 35
    minimum = Settings.model_validate({"retention": {"raw_days": 31}})
    assert minimum.retention.raw_days == 31


def test_web_query_limits_have_small_host_defaults():
    web = Settings.model_validate({}).web
    assert web.enable_docs is False
    assert web.max_query_concurrency == 4
    assert web.query_queue_timeout_s == 1
    assert web.query_timeout_s == 12
    assert web.stats_cache_ttl_s == 15
    assert web.ranking_user_limit == 200


def test_load_settings_requires_real_settings_file(tmp_path, monkeypatch):
    """example 只能用于复制，生产/开发启动都不能把它静默当成真实配置。"""
    from gpumon import config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.example.toml").write_text(
        "[web]\nport = 9999\n", encoding="utf-8"
    )
    monkeypatch.setattr(config, "ROOT", tmp_path)
    config.load_settings.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="settings.toml"):
            config.load_settings()
    finally:
        config.load_settings.cache_clear()
