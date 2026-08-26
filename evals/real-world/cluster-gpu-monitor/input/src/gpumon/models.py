"""数据模型 —— inventory/settings 的结构，以及采集结果的内部 DTO。

这里只放纯数据结构，不含 IO。pydantic 负责校验与默认值。
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ConfigKey = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
OptionalConfigKey = Annotated[
    str,
    StringConstraints(
        max_length=128,
        pattern=r"^(?:[A-Za-z0-9][A-Za-z0-9._-]*)?$",
    ),
]
SshAlias = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:@%+-]*$",
    ),
]
Status = Literal["active", "planned", "retired"]
Vendor = Literal["nvidia", "amd"]
BadgeTone = Literal["cyan", "gold", "green", "violet", "neutral"]
Palette = Literal["lime", "violet", "azure", "amber", "rose", "teal", "indigo", "slate"]
HardwareId = Annotated[str, StringConstraints(min_length=1, max_length=256)]
OptionalShortText = Annotated[str, StringConstraints(min_length=1, max_length=256)]
# 面向网页的自定义文案既可以沿用单字符串，也可以按前端 locale 配多种翻译。
# dict 保留 YAML 声明顺序；当前语言缺失时，前端据此回退到第一条翻译。
LanguageCode = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=35,
        pattern=r"^[A-Za-z][A-Za-z0-9]{0,7}(?:-[A-Za-z0-9]{1,8})*$",
    ),
]
ShortLocalizedString = Annotated[str, StringConstraints(min_length=1, max_length=128)]
LongLocalizedString = Annotated[str, StringConstraints(min_length=1, max_length=2048)]
LocalizedShortText = ShortLocalizedString | Annotated[
    dict[LanguageCode, ShortLocalizedString],
    Field(min_length=1, max_length=32),
]
LocalizedLongText = LongLocalizedString | Annotated[
    dict[LanguageCode, LongLocalizedString],
    Field(min_length=1, max_length=32),
]
MAX_GPUS_PER_HOST = 1024
MAX_PROCESSES_PER_HOST = 4096
MAX_SSH_OUTPUT_PER_HOST_BYTES = 16 * 1024 * 1024
MAX_SSH_OUTPUT_IN_FLIGHT_BYTES = 64 * 1024 * 1024


class ConfigModel(BaseModel):
    """配置模型统一拒绝未知字段，避免拼写错误被静默忽略。"""

    model_config = ConfigDict(extra="forbid")


class SampleModel(BaseModel):
    """远端探测数据不可信；字段赋值时也必须持续执行边界校验。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ---------------------------------------------------------------------------
# inventory.yaml 结构
# ---------------------------------------------------------------------------
class HostCfg(ConfigModel):
    key: ConfigKey                       # 稳定标识，历史按它关联
    ssh_alias: SshAlias                  # ~/.ssh/config 别名，采集用
    display_name: str = Field(min_length=1, max_length=256)
    gpu_count: int | None = Field(default=None, ge=1, le=4096)  # 缺省时取 defaults
    status: Status = "active"
    note: LocalizedLongText | None = None
    # GPU 厂商：已知且固定时显式填写可跳过每轮远端自动探测；留空时按工具顺序识别。
    vendor: Vendor | None = None
    meta: dict[str, Any] = Field(default_factory=dict, max_length=128)


class BadgeCfg(ConfigModel):
    """集群卡片上的自定义标签，可挂多枚。text 必填，其余可选。

    tone 是预设的语义色名（cyan/gold/green/violet/neutral），不接受任意 CSS 色值——
    保证标签色不与利用率语义色、算力域家族色互相干扰。

    key 只在「标签库」（Inventory.badge_library）里需要填：填了就能被算力域/集群
    按名字引用，达到一处定义、多处复用。直接内联写在 badges 下的标签不用填 key。
    """
    key: ConfigKey | None = None
    text: LocalizedShortText
    mark: str | None = Field(default=None, max_length=16)  # 前缀符号，如 "◆"
    tooltip: LocalizedLongText | None = None
    tone: BadgeTone = "cyan"


class CapacityGroupCfg(ConfigModel):
    key: ConfigKey
    name: str = Field(min_length=1, max_length=256)
    sort_order: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    description: LocalizedLongText | None = None
    # 色带名（lime/violet/azure/amber/rose/teal/indigo/slate）。
    # 留空则按 sort_order 自动轮转分配，不会撞成灰色。
    palette: Palette | None = None
    # 算力域也能挂标签：写标签库的 key（复用），或内联一枚 {text:..., tone:...}
    badges: list[ConfigKey | BadgeCfg] = Field(default_factory=list, max_length=64)


class ClusterCfg(ConfigModel):
    key: ConfigKey
    name: str = Field(min_length=1, max_length=256)
    sort_order: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    # 留空 = 落到 defaults.fallback_group_key
    capacity_group: OptionalConfigKey = ""
    status: Status = "active"
    note: LocalizedLongText | None = None
    # 每项可以是标签库的 key（字符串，复用）或内联的完整定义
    badges: list[ConfigKey | BadgeCfg] = Field(default_factory=list, max_length=64)
    hosts: list[HostCfg] = Field(default_factory=list, max_length=4096)

    def resolved_badges(self, library: dict[str, BadgeCfg] | None = None) -> list[BadgeCfg]:
        """最终标签序列：badges 里的字符串按标签库查表展开，内联项原样保留。

        查不到的 key 会被跳过（load_inventory 已在启动时校验过，正常运行不会出现）。
        """
        return _expand_badges(self.badges, library)


def _expand_badges(items: list[ConfigKey | BadgeCfg],
                   library: dict[str, BadgeCfg] | None) -> list[BadgeCfg]:
    """把 badges 列表里的「库 key 字符串」换成库里的定义，内联项原样保留。"""
    lib = library or {}
    out: list[BadgeCfg] = []
    for it in items:
        if isinstance(it, str):
            found = lib.get(it)
            if found is not None:
                out.append(found)
        else:
            out.append(it)
    return out


class Defaults(ConfigModel):
    gpu_count: int = Field(default=8, ge=1, le=4096)
    poll_interval_s: int = Field(default=30, ge=1, le=86_400)
    # 集群未声明 capacity_group、或引用了不存在的域时兜底用的域。
    fallback_group_key: ConfigKey = "default"
    fallback_group_name: str = Field(default="未分组", min_length=1, max_length=256)


# 内置色带名，顺序即自动轮转顺序。见 web/js/components.js 的 BANDS。
PALETTES = ["lime", "violet", "azure", "amber", "rose", "teal", "indigo", "slate"]


class Inventory(ConfigModel):
    version: Literal[1] = 1
    defaults: Defaults = Field(default_factory=Defaults)
    # 不预置任何机构名——没声明就由 resolved_groups() 兜一个中性的"未分组"。
    capacity_groups: list[CapacityGroupCfg] = Field(default_factory=list, max_length=4096)
    clusters: list[ClusterCfg] = Field(max_length=4096)
    # 标签库：一处定义，算力域/集群按 key 引用。每项必须带 key。
    badge_library: list[BadgeCfg] = Field(default_factory=list, max_length=4096)

    @property
    def badges_by_key(self) -> dict[str, BadgeCfg]:
        """标签库的 key → 定义索引。没写 key 的条目忽略（校验时已报错）。"""
        return {b.key: b for b in self.badge_library if b.key}

    def group_badges(self, group: CapacityGroupCfg) -> list[BadgeCfg]:
        """算力域的最终标签序列（库引用已展开）。"""
        return _expand_badges(group.badges, self.badges_by_key)

    def cluster_badges(self, cluster: ClusterCfg) -> list[BadgeCfg]:
        """集群的最终标签序列（库引用已展开）。"""
        return cluster.resolved_badges(self.badges_by_key)

    def group_key_of(self, cluster: ClusterCfg) -> str:
        """集群实际归属的算力域 key：没写或写了不存在的域，都落到兜底域。"""
        declared = {g.key for g in self.capacity_groups}
        if cluster.capacity_group and cluster.capacity_group in declared:
            return cluster.capacity_group
        return cluster.capacity_group or self.defaults.fallback_group_key

    def resolved_groups(self) -> list[CapacityGroupCfg]:
        """最终算力域列表：显式声明的 + 集群引用到但未声明的 + 兜底域，按 sort_order 排序。

        palette 未指定时按位置轮转分配，保证第 3、4、5… 个域也有独立色系，
        不会像旧版那样全部掉进灰色 FALLBACK。
        """
        out = list(self.capacity_groups)
        known = {g.key for g in out}
        for c in self.clusters:
            k = self.group_key_of(c)
            if k in known:
                continue
            known.add(k)
            is_fallback = k == self.defaults.fallback_group_key
            out.append(CapacityGroupCfg(
                key=k,
                name=self.defaults.fallback_group_name if is_fallback else k,
                sort_order=999,
            ))
        out.sort(key=lambda g: (g.sort_order, g.key))
        for i, g in enumerate(out):
            if not g.palette:
                g.palette = PALETTES[i % len(PALETTES)]
        return out

    def iter_hosts(self):
        """展开成 (cluster, host, gpu_count) 三元组，gpu_count 已套用默认值。"""
        for c in sorted(self.clusters, key=lambda x: x.sort_order):
            for h in c.hosts:
                yield c, h, (h.gpu_count or self.defaults.gpu_count)


# ---------------------------------------------------------------------------
# settings.toml 结构
# ---------------------------------------------------------------------------
class CollectorSettings(ConfigModel):
    poll_interval_s: int = Field(default=30, ge=1, le=86_400)
    ssh_connect_timeout_s: int = Field(default=8, ge=1, le=300)
    ssh_total_timeout_s: int = Field(default=20, ge=1, le=3600)
    max_concurrency: int = Field(default=8, ge=1, le=512)
    cpu_sample_gap_s: int = Field(default=1, ge=1, le=60)
    # stdout + stderr 共用这一预算；超限立即终止 ssh，防止异常目标耗尽本机内存。
    ssh_output_limit_bytes: int = Field(
        default=4 * 1024 * 1024,
        ge=64 * 1024,
        le=MAX_SSH_OUTPUT_PER_HOST_BYTES,
    )

    @model_validator(mode="after")
    def validate_ssh_memory_budget(self) -> CollectorSettings:
        """限制并发管道里可同时保留的原始 SSH 输出。"""
        in_flight = self.max_concurrency * self.ssh_output_limit_bytes
        if in_flight > MAX_SSH_OUTPUT_IN_FLIGHT_BYTES:
            raise ValueError(
                "max_concurrency * ssh_output_limit_bytes 不能超过 64 MiB"
            )
        return self


class RetentionSettings(ConfigModel):
    # 用户排行的最长窗口是 1m（30 天），因此原始进程样本不能再允许低于 31 天。
    # 默认留到 35 天，给清理任务执行时点和少量时间偏差留出余量。
    raw_days: int = Field(default=35, ge=31, le=36_500)
    rollup_5m_days: int = Field(default=30, ge=1, le=36_500)
    # 1 小时聚合保留天数；须 > 最长时间窗(1m=30d)，留足余量
    rollup_1h_days: int = Field(default=400, ge=1, le=36_500)


class DbSettings(ConfigModel):
    path: str = Field(default="data/gpumon.db", min_length=1, max_length=4096)


class WebSettings(ConfigModel):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=255)
    port: int = Field(default=8848, ge=1, le=65_535)
    enable_docs: bool = False
    max_query_concurrency: int = Field(default=4, ge=1, le=32)
    query_queue_timeout_s: float = Field(
        default=1.0, ge=0, le=30, allow_inf_nan=False
    )
    query_timeout_s: float = Field(
        default=12.0, ge=1, le=120, allow_inf_nan=False
    )
    stats_cache_ttl_s: int = Field(default=15, ge=0, le=300)
    ranking_user_limit: int = Field(default=200, ge=1, le=1000)


class PrivacySettings(ConfigModel):
    mask_users: bool = False


class BackupSettings(ConfigModel):
    enabled: bool = True          # 是否启用自动备份
    keep_count: int = Field(default=3, ge=1, le=1000)  # 保留备份数量


class Settings(ConfigModel):
    collector: CollectorSettings = Field(default_factory=CollectorSettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    db: DbSettings = Field(default_factory=DbSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)


# ---------------------------------------------------------------------------
# 采集结果 DTO（采集器解析 remote_probe 输出后产出，再交给 store 写库）
# ---------------------------------------------------------------------------
class GpuSample(SampleModel):
    index: int = Field(ge=0, le=4095)
    uuid: HardwareId
    name: OptionalShortText | None = None
    vendor: Vendor | None = None   # nvidia / amd，仅用于展示与排障，不参与历史关联
    util_gpu: int | None = Field(default=None, ge=0, le=100)
    util_mem: int | None = Field(default=None, ge=0, le=100)
    mem_used_mib: int | None = Field(default=None, ge=0, le=1_000_000_000)
    mem_total_mib: int | None = Field(default=None, ge=0, le=1_000_000_000)
    temp_c: int | None = Field(default=None, ge=-273, le=1000)
    power_w: float | None = Field(
        default=None, ge=0, le=1_000_000, allow_inf_nan=False
    )


class ProcSample(SampleModel):
    gpu_uuid: HardwareId
    pid: int = Field(ge=1, le=2_147_483_647)
    username: OptionalShortText | None = None
    comm: str | None = Field(default=None, min_length=1, max_length=1024)
    mem_used_mib: int | None = Field(default=None, ge=0, le=1_000_000_000)


class HostSample(SampleModel):
    ncpu: int | None = Field(default=None, ge=1, le=1_048_576)
    load1: float | None = Field(default=None, ge=0, le=1_000_000_000, allow_inf_nan=False)
    load5: float | None = Field(default=None, ge=0, le=1_000_000_000, allow_inf_nan=False)
    load15: float | None = Field(default=None, ge=0, le=1_000_000_000, allow_inf_nan=False)
    cpu_util_pct: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    mem_total_mib: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    mem_avail_mib: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    mem_used_mib: int | None = Field(default=None, ge=0, le=1_000_000_000_000)


class ProbeResult(SampleModel):
    """一台机器一轮采集的完整结果。ok=False 表示该机本轮失败（超时/SSH错误）。"""
    host_key: ConfigKey
    ok: bool
    error: str | None = Field(default=None, max_length=512)
    # ok=True 时仍可能因整轮资源预算而省略部分明细；warning 会写入采集状态。
    warning: str | None = Field(default=None, max_length=512)
    vendor: Literal["nvidia", "amd", "none"] | None = None
    remote_hostname: OptionalShortText | None = None
    gpus: list[GpuSample] = Field(default_factory=list, max_length=MAX_GPUS_PER_HOST)
    procs: list[ProcSample] = Field(default_factory=list, max_length=MAX_PROCESSES_PER_HOST)
    host: HostSample | None = None

    @model_validator(mode="after")
    def validate_gpu_identity(self) -> ProbeResult:
        """同一轮的 GPU index/UUID 必须唯一，避免错误 upsert 和进程归属。"""
        indices = [g.index for g in self.gpus]
        uuids = [g.uuid for g in self.gpus]
        if len(indices) != len(set(indices)):
            raise ValueError("同一轮存在重复 GPU index")
        if len(uuids) != len(set(uuids)):
            raise ValueError("同一轮存在重复 GPU UUID")
        return self
