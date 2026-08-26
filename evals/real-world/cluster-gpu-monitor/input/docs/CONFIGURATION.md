# 配置参考

简体中文 | [English](CONFIGURATION.en.md) | [文档目录](README.md) | [项目首页](../README.md)

本文是字段手册。第一次运行先看 [README 快速开始](../README.md#快速开始)；采集与指标口径见
[架构与设计取舍](ARCHITECTURE.md)，生产安装见[部署指南](DEPLOYMENT.md)。

两个文件，都在 `config/` 下，都**不入库**（`.gitignore` 已排除）：

| 文件 | 管什么 | 改完要做什么 |
| --- | --- | --- |
| `inventory.yaml` | 有哪些机器、怎么分组、怎么显示 | `systemctl restart gpumon-collector`（退役机器再加 `gpumon-web`） |
| `settings.toml` | 采集周期、保留天数、端口、隐私 | 重启对应服务（采集参数→collector，端口→web） |

先从样例复制：

```bash
cp config/inventory.example.yaml config/inventory.yaml
cp config/settings.example.toml config/settings.toml
uv run gpumon config-check          # 任何改动后都先跑这个
```

`config-check` 会把最终生效的算力域、色带分配、每个集群的标签、每台机的期望卡数
全部打印出来。**配错了在这一步就能看见**，不用等网页。

---

## inventory.yaml

### 三层拓扑

层级是固定的三层，只要按这个结构填，网页、统计表、排行、配色全部自适应：

```
算力域 (capacity_group)     ← 最粗的分组，比如"自有" / "租用" / "某合作方"
  └─ 集群 (cluster)          ← 一批机器，通常同机房 / 同一批采购 / 同一个跳板
       └─ 服务器 (host)      ← 一台物理机
            └─ GPU           ← 首轮采集自动发现，不用手写
```

GPU 不需要在配置里声明——采集器第一次连上就会把卡的 UUID、型号、显存写进库。
你只需要填 `gpu_count` 作为**期望值**，用于"掉卡"检测。

### 最小可用配置

```yaml
version: 1

clusters:
  - key: my-cluster
    name: "我的集群"
    hosts:
      - { key: node-1, ssh_alias: node-1, display_name: "节点 1" }
```

没写 `capacity_groups`、没写 `capacity_group` 也能跑——会落到一个中性的兜底域
（默认叫"未分组"，名字可改，见 `defaults`）。

### 顶层字段

```yaml
version: 1                    # 配置格式版本，固定 1

defaults:
  gpu_count: 8                # 主机没写 gpu_count 时用这个
  poll_interval_s: 30         # 兼容字段；实际采集周期以 settings.toml 为准
  fallback_group_key: default     # 集群没写 capacity_group 时归到哪个域
  fallback_group_name: "未分组"    # 该兜底域在网页上的显示名
```

### 多语言自定义文案

下列字段既可写普通字符串，也可写「语言代码 → 翻译」映射：

| 位置 | 字段 |
| --- | --- |
| 标签库与内联标签 | `text`、`tooltip` |
| 算力域 | `description` |
| 集群、主机 | `note` |

语言代码应与前端 `web/js/i18n.js` 使用的 locale 一致；项目默认是 `zh` 和 `en`。
也可使用 `zh-CN` 这类带地区的代码。旧的单字符串写法完全兼容，会在所有界面语言下原样显示。

```yaml
badge_library:
  - key: self-built
    text:
      zh: "自建"                 # 第一条，也是缺少目标语言时的回退文案
      en: "Self-built"
    tooltip:
      zh: "本地自行装机"
      en: "Built locally"
```

前端先找当前 locale 的精确翻译，再找同一基础语言（如 `zh-CN` → `zh`），最后按 YAML
顺序使用第一条已有翻译。每个字段独立回退：例如 `text` 有两种翻译、`tooltip` 只写一种也能用。
映射和其中的翻译都不能为空。

### capacity_groups（算力域）

```yaml
capacity_groups:
  - key: own                  # 稳定标识，集群通过它引用
    name: "自有算力"          # 网页显示名，随便改
    sort_order: 1             # 排序，小的在前
    palette: lime             # 可选：指定色系
    description: "自购自管"   # 可选：显示在域标题下；也可写语言映射
    badges: [self-built]      # 可选：域级标签，见下面 badges 一节
```

**palette 可以不写。** 不写就按 `sort_order` 从内置色带里轮转分配，
保证每个域都有独立可辨的色系。内置八条：

| 色带 | 色调 | 色带 | 色调 |
| --- | --- | --- | --- |
| `lime` | 黄绿 → 绿 → 青蓝 | `rose` | 玫红 → 紫红 |
| `violet` | 品红 → 紫罗兰 | `teal` | 松绿 → 青 |
| `azure` | 青 → 宝蓝 | `indigo` | 靛蓝 → 群青 |
| `amber` | 琥珀 → 赭橙 | `slate` | 中性灰蓝 |

超过 8 个域也没问题：前端会按黄金角生成新色相，不会退化成一片灰。

色带内部还有两级区分：**同域的不同集群沿色带铺开色相，同集群的不同机器拉明度**。
所以一眼就能看出"这几台是一个集群的"。

> 利用率的红/橙/黄/绿/灰是**语义色**，含义固定，和算力域家族色是两套体系，互不干扰。

### clusters（集群）

```yaml
clusters:
  - key: cluster-a            # 稳定标识，历史按它关联，上线后别改
    name: "A 集群"            # 显示名，随时可改
    sort_order: 1
    capacity_group: own       # 引用上面的域 key；留空 = 兜底域
    status: active            # active（默认） / planned / retired
    note: "集群备注，显示在总览与集群页；也可写语言映射"
    badges: [...]             # 见下节
    hosts: [...]
```

### badges（自定义标签）

小胶囊标签，用来标注任何你想强调的属性。**算力域和集群都能挂**，写法完全一样
（主机不支持）。

推荐做法：把标签定义在顶层的 `badge_library` 里，各处只写 key 引用。这样
「自建」这类会出现在多个地方的标签只定义一次，改文案/tooltip 时所有引用处一起变。

```yaml
badge_library:
  - key: self-built
    text: "自建"                       # 必填；也可写语言映射
    mark: "◆"                          # 可选：前缀符号
    tone: cyan                         # 可选：cyan/gold/green/violet/neutral
    tooltip: "本地装机，账号自助申请"    # 可选：悬停说明；也可写语言映射
  - key: infiniband
    text: "InfiniBand"
    tone: green

capacity_groups:
  - key: own
    name: "自有算力"
    badges: [self-built]               # 算力域挂标签

clusters:
  - key: cluster-a
    name: "A 集群"
    badges: [self-built, infiniband]   # 集群引用同样两枚，取到的是同一份定义
```

只在一处用到的标签不必进库，直接内联；两种写法可以混着写，顺序按声明顺序：

```yaml
    badges:
      - self-built                                    # 库引用
      - { text: "ROCm", tone: gold, tooltip: "需要 ROCm 版框架" }   # 内联
```

- 一个域/集群可挂任意多枚，**超过 3 枚自动折叠成 `+N`**，悬停展开完整列表。
- `tone` 只接受这五个预设名，不接受任意 CSS 色值——这是有意的，防止标签色和
  利用率语义色/算力域家族色撞在一起。
- 引用了库里没有的 key 会在启动时报错并列出可选值，不会静默把标签丢掉。

> **从 v0.3.0 前的配置升级**：`configured_by: "运维组"` 已移除。它原本自动合成一枚
> `◆ 运维组 配置`。改成库里定义一枚、集群 `badges` 引用它即可；老字段留着会在启动时
> 报错并提示改法（不静默忽略，否则那枚标签会无声消失）。

### hosts（服务器）

```yaml
    hosts:
      - key: node-1                    # 稳定标识，历史按它关联，上线后别改
        ssh_alias: my-node-1           # ~/.ssh/config 里的别名
        display_name: "节点 1"         # 显示名，随时可改
        gpu_count: 8                   # 期望卡数，缺省取 defaults
        status: active                 # active（默认） / planned / retired
        vendor: amd                    # 可选；已知厂商时填写可跳过每轮自动探测
        note: "待接入主机的悬停备注；也可写语言映射"
        meta:
          gpu_model: "AMD Instinct MI300X"   # 待接入占位卡上显示的型号
```

**必填字段**：`key`、`ssh_alias`、`display_name`。其余都有默认值。

`key` 和 `ssh_alias` 的分工很关键：

- **`key` 是历史的锚点**，库里所有采样都挂在它上面，**永远不要改**。
- **`ssh_alias` 是怎么连上去**，可以随时改。换部署机、加跳板、改 IP，
  只改 ssh config 和这个字段，`key` 不动 → **历史曲线连续不断**。

**跨网段 / 内网机器怎么接**：在部署机的 `~/.ssh/config` 里用 `ProxyJump` 声明跳板，
`inventory.yaml` 只写内网机器的别名。采集器执行 `ssh <别名>` 时 ssh 会自动走跳板。

```sshconfig
# ~/.ssh/config（部署机上，采集器用户的配置）
Host my-bastion
  HostName 1.2.3.4
  User root

Host my-node-1
  HostName 10.0.1.100         # 内网地址
  User ubuntu
  ProxyJump my-bastion        # ← 真正的跳板声明在这里
```

然后 `inventory.yaml` 里直接写 `ssh_alias: my-node-1`，不需要额外字段。

**`meta.gpu_model` 什么时候需要写**：只在 `status: planned` 待接入占位时需要——
因为机器还连不上、采不到数据，占位卡要显示"8 张 NVIDIA H100"就得从 `meta` 读。
正常在线机器的型号来自采集（`nvidia-smi -L` / `rocm-smi --showproductname`），
存进数据库后就算 `meta` 没写、机器离线了，网页照样显示型号——只要它活着时被采集过至少一次。

### status 的三个值

| 值 | 采集器 | 网页 | 数据库 | 用在什么时候 |
| --- | --- | --- | --- | --- |
| `active` | 正常探测 | 正常显示 | 正常写入 | 默认 |
| `planned` | 不探测 | 显示占位卡（灰色 `--`） | 无 | 机器还没到 / 还没拿到权限，先把位置占上 |
| `retired` | 停止探测 | 整台隐去 | **历史一行不删** | 机器退租下架 |

**退役机器不要从 inventory 里删条目。** 删了配置、库里的历史行还在，
网页反而会挂一张永久离线的幽灵卡。标 `retired` 才是正确做法：
采集器不再连它，网页各处（总览 / 集群页 / 主机页 / 健康灯 / 使用人排行）都不再出现它，
但历史数据完整保留，日后要对账随时能查。

标完 `retired` 需要重启**两个**服务：`gpumon-collector`（停止探测）和
`gpumon-web`（清掉 inventory 的缓存）。

### vendor 与 AMD

`vendor` 留空时，远端探测脚本按顺序试 `nvidia-smi` → `amd-smi` → `rocm-smi`，
哪个真能跑通就用哪个。这个判断每轮都会执行，不会缓存：正常 NVIDIA 主机会因此额外执行
一次 `nvidia-smi -L`；AMD 主机还可能先尝试排在前面的工具。

厂商已知且固定时，建议显式填写 `nvidia` 或 `amd`，减少目标机上的 SMI 调用。只有厂商未知、
硬件可能更换，或需要同一份 inventory 自动适配不同机器时才留空：

```yaml
      - { key: nvidia-1, ssh_alias: nvidia-1, display_name: "NVIDIA-1", vendor: nvidia }
      - { key: amd-1, ssh_alias: amd-1, display_name: "AMD-1", vendor: amd }
```

显式填写还可以避免误判，例如机器同时装有多套厂商工具，或者驱动存在但当前没有可用卡。

> AMD 支持是按 `rocm-smi` / `amd-smi` 的官方输出格式实现并用构造样本做了单测的，
> **尚未在真实 AMD 硬件上验证**。接第一台 AMD 机器时，建议先跑
> `./scripts/probe_one.sh <alias>` 看原始输出，确认 `##VENDOR` / `##AMDSMI_*` 段有内容。

---

## settings.toml

```toml
[collector]
poll_interval_s = 30        # 每轮采集间隔。也是 GPU·小时的计量粒度
ssh_connect_timeout_s = 8   # SSH 建连超时
ssh_total_timeout_s = 20    # 单台机一轮的整体超时（含远端 sleep）
max_concurrency = 8         # 同时 SSH 几台。机器多可以调大，注意跳板机承受能力
cpu_sample_gap_s = 1        # 远端两次读 /proc/stat 的间隔，用于算 CPU 利用率
ssh_output_limit_bytes = 4194304 # 单机单轮输出上限（最高 16 MiB），超限终止 SSH

[retention]
raw_days = 35               # 原始样本保留天数（最低 31 天）
rollup_5m_days = 30         # 5 分钟聚合保留天数
rollup_1h_days = 400        # 1 小时聚合保留天数

[db]
path = "data/gpumon.db"     # 相对项目根

[web]
host = "127.0.0.1"          # 反代后面就保持 127.0.0.1；要直接访问改 0.0.0.0
port = 8848
enable_docs = false          # 生产关闭 /docs、/redoc、/openapi.json
max_query_concurrency = 4    # 昂贵查询并发上限
query_queue_timeout_s = 1    # 查询槽位满时排队上限；超时返回 503
query_timeout_s = 12         # 单个 SQLite 查询连接的执行上限
stats_cache_ttl_s = 15       # 历史统计短缓存；0 表示关闭
ranking_user_limit = 200     # 排行最多返回多少人

[privacy]
mask_users = false          # true 时使用人显示成 a***e

[backup]
enabled = true              # 是否启用定时备份（外部调度器调用 --scheduled 时检查）
keep_count = 3              # 保留最近几个备份
```

### Web 查询边界

Web 默认只同时执行 4 个昂贵统计查询；槽位满后最多等 1 秒，单个 SQLite 只读连接
最多执行 12 秒。超出任一边界会返回带 `Retry-After` 的 HTTP 503，而不是继续堆积线程和
内存。历史均值、时序和排行按 15 秒短缓存复用，排行超过 200 人时只返回前 200 名并在
响应/UI 标明截断。小规格宿主建议保留这些默认值；大部署应先在数据库副本测量，再逐项调大。

`enable_docs=false` 只关闭 FastAPI 的交互式文档和 OpenAPI JSON，不影响仪表盘 API。
开发环境需要调试接口时可显式设为 `true`。

### 备份配置

程序内部没有定时器。原生部署由 systemd timer 在每天 04:00 调度；Docker Compose 部署由
宿主的唯一外部调度器调用一次性 backup 服务。

- `enabled`: 是否启用定时备份。设为 `false` 时外部调度器仍可触发，但
  `gpumon backup --scheduled` 会安全跳过；手工 `gpumon backup` 不受影响。
- `keep_count`: 保留最近几个备份文件。默认 3 个，即最多恢复到 3 天前。

备份先由 SQLite backup API 写入同目录临时文件，通过 `quick_check`、设为 `0600`
并 fsync 后才原子改名；只有新备份成功发布后才会清理旧文件。

**原生部署修改备份时间**只更新 systemd timer，避免 settings 与实际调度产生两个真相来源：

```bash
# 编辑 timer（OnCalendar 一行）
sudo systemctl edit --full gpumon-backup.timer

# 示例：改成每天早上 8 点
# OnCalendar=*-*-* 08:00:00

# 重新加载并重启 timer
sudo systemctl daemon-reload
sudo systemctl restart gpumon-backup.timer
```

手动备份：`uv run gpumon backup`（立即备份一次，按 `keep_count` 清理旧备份）。
Docker 的手工与定时命令见 [Docker Compose 指南](DOCKER.md#7-备份与定时调度)。

### 保留天数怎么定（有个坑）

三张表各管一段时间范围，查询时按窗口自动选表：

- **≤24h 的窗口**走 5 分钟聚合表
- **>24h 的窗口**走 1 小时聚合表（不碰原始表，所以长窗口也很快）
- **使用人排行扫原始 `sample_proc` 表**

最后这条是坑所在：**`raw_days` 必须 ≥ 你想用的最长时间窗 + 余量**。
现在配置下限为 31 天，默认 `raw_days = 35`，在 30 天窗口之外再留 5 天余量。
旧版配置若仍写 7/14/30 天，`config-check` 和服务启动会直接拒绝，避免“近 1 月使用人
排行”无提示地少算。升级前先把真实 `settings.toml` 调到至少 31，推荐保持 35。

`rollup_1h_days` 同理要大于最长窗口，默认 400 天留了充足余量。

### 并发与跳板

`max_concurrency` 是同时发起的 SSH 数。机器多的时候想调大，但要注意：
如果这些机器都走同一个跳板，跳板的 `MaxSessions` / `MaxStartups` 会先成为瓶颈，
表现是部分机器随机超时。稳妥做法是先小步调大（8 → 16），观察
`/api/collector/status` 里有没有新增的超时。

配置校验还要求 `max_concurrency * ssh_output_limit_bytes <= 64 MiB`，避免同时保留过多
SSH 输出。解析后每台最多保留 4096 条进程样本，整轮最多 65536 条；异常超量时优先
保留 GPU/主机指标，省略该机进程明细并在采集状态里给出告警。

---

## 改完之后

| 改了什么 | 要做什么 |
| --- | --- |
| 加机器 / 加集群 / 改显示名 / 改标签 | `systemctl restart gpumon-collector` |
| 标了 `retired` | `systemctl restart gpumon-collector gpumon-web` |
| 改采集参数（周期 / 超时 / 并发） | `systemctl restart gpumon-collector` |
| 改端口 / 监听地址 / 隐私开关 | `systemctl restart gpumon-web` |
| 改保留天数 | 下次自动清理生效，或 `uv run gpumon rollup-once` |
| 只改了 `web/` 下的前端文件 | 什么都不用做，刷新浏览器即可 |

验证改动生效：

```bash
uv run gpumon config-check                      # 配置层面
curl -s 127.0.0.1:8848/api/collector/status     # 每台机在线 / 卡数 / 最近错误
curl -s 127.0.0.1:8848/api/health               # 最近一次采样多久之前
```
