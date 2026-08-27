<p align="center">
  <img src="assets/deslop-banner.svg" alt="deslop — 面向由 Agent 维护的代码库，以删除为先的清理工具" width="100%">
</p>

<h1 align="center">deslop</h1>

<p align="center">
  <strong>面向由 Agent 维护的代码库，以删除为先的 Agent Skill</strong>
</p>

<p align="center"><strong>简体中文</strong> · <a href="README.md">English</a></p>

<p align="center">
  以证据为依据，在保留真实行为的同时减少累积的冗余机制。
</p>

<p align="center">
  <a href="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml"><img src="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml/badge.svg" alt="验证工作流"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f.svg?style=flat-square" alt="MIT 许可证"></a>
  <a href="skills/deslop/"><img src="https://img.shields.io/badge/Agent%20Skill-Codex%20%2B%20Claude%20Code-0969da.svg?style=flat-square" alt="兼容 Codex 和 Claude Code 的 Agent Skill"></a>
  <a href="#安全模型"><img src="https://img.shields.io/badge/default-read--only-6e7781.svg?style=flat-square" alt="默认只读"></a>
  <a href="evals/real-world/cluster-gpu-monitor/README.zh-CN.md"><img src="https://img.shields.io/badge/field%20trial-manually%20adjudicated-8250df.svg?style=flat-square" alt="经人工裁定的现场试验"></a>
</p>

`deslop` 会审计代码库，并在获得明确授权时，移除由编码 Agent 反复实现与修正所累积的复杂性。这类循环往往会留下相互重叠的回归测试、由生产者自行验证生产者的检查，以及掩盖故障而非履行当前契约的回退层。

这是语义层面的删减，而不是源代码美化。`deslop` 不是格式化工具、风格人性化工具、测试数量最小化工具，也不主张全面禁止防御性代码，更不会自动获得编辑仓库的权限。它沿着论证链追溯至独立证据，并保留那些契约仍然真实存在或尚不确定的行为。

> **缩减测试表面，而不是行为表面。**

## 目标对象

以下百分比表示设计优先级，而非实际出现频率的测量结果。

| 优先级 | 目标 | 判断问题 |
| ---: | --- | --- |
| ~50% | **测试套件膨胀** | 每项测试是否借助独立判定依据保护一项独特的外部行为？ |
| ~25% | **表演式验证** | 验证器能否独立于生产者失败，还是二者共享相同的信息与故障域？ |
| ~25% | **防御性代码／回退机制膨胀** | 恢复路径是在履行当前契约，还是仅仅掩盖意外的内部错误？ |

一般性的死代码、包装层、抽象和注释属于次要目标。只有当它们归属于上述某类问题，或有直接且高置信度的删除证据时，才需要处理。

## 删减机制，保留行为

| 移除 | 保留 |
| --- | --- |
| 自我论证或重复的测试 | 不同的成功、拒绝、错误及边界情况行为 |
| 没有独立使用者的校验和、回执或验证器 | 跨越真实故障边界的持久化与损坏检查 |
| 推测性的或已过时的回退链 | 受支持的兼容性与有文档记录的协议行为 |
| 受信任调用图内部的重复防御 | 外部边界与不受信任边界处的真实处理逻辑 |
| 没有独立用途的包装层／测试簇 | 安全、事务、并发、资源及科学不变量 |

与某种代码异味相似只是线索，并非结论。证据不足时，默认保留安全与信任边界、受支持的调用方、持久化格式和数值约束。

## 快速开始

### Codex：将 v0.2.1 安装为独立 Skill

使用以下 GitHub Skill URL 调用内置安装器：

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/v0.2.1/skills/deslop
```

若希望使用可审查的本地检出，请将运行时目录符号链接到 Codex 规范的用户 Skill 位置：

```bash
git clone --branch v0.2.1 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
```

Codex 支持以符号链接方式安装的 Skill 目录，并会自动检测变更。带标签的 v0.2.1 路径是当前已发布且固定版本的独立 Skill；[`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) 是开发分支，可能包含尚未发布的变更。

### Claude Code：从 GitHub 安装 Plugin

在 Claude Code 中，将此仓库添加为 marketplace 并安装 Plugin：

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

规范的 Plugin 命令是 `/deslop:deslop`。若使用本地检出，请在仓库根目录通过 `claude --plugin-dir .` 直接加载仓库。Claude marketplace 从 `main` 分发 0.2.1 版 Plugin，对应的 v0.2.1 标签固定了同一版本。本补丁版本新增 Claude Code 打包和双语文档；运行时 Skill 载荷与 v0.2.0 保持不变。

### 一份检出，同时供两个宿主独立发现

同一份已发布运行时载荷可以链接到各宿主的用户 Skill 目录：

```bash
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

只需为你使用的宿主创建对应链接，并且仅在目标不存在时运行相应的 `ln` 命令。独立安装的 Claude Code Skill 通过 `/deslop` 调用。有关安装范围、从 v0.1.0 迁移、更新、移除及更安全的先审查后操作流程，请参阅[入门指南](docs/getting-started.zh-CN.md)。`deslop` 是独立的社区项目，并非 OpenAI 或 Anthropic 的产品。

### 分发状态

共享的 [`skills/deslop/`](skills/deslop/) 载荷遵循开放的 Agent Skills 结构，Codex 与 Claude Code 均原样使用。[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) 和 [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) 提供 Claude Code 打包配置。Codex Plugin 分发仍暂不提供，因为经测试的 Codex 宿主虽然安装并缓存了仅含 Skills 的 Plugin，却没有注册其中捆绑的 Skill；Codex 的独立安装方式仍受支持。请参阅[分发兼容性说明](docs/development.zh-CN.md#分发兼容性说明)。

### 明确调用

| 宿主与分发方式 | 命令名称 |
| --- | --- |
| Codex 独立 Skill | `$deslop` |
| Claude Code 独立 Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

在各宿主使用的命令名称后追加相同的模式与范围参数：

| 参数 | 效果 |
| --- | --- |
| 无 | 对既定范围进行只读审计 |
| `audit` | 明确进行只读审计 |
| `apply` | 在范围内应用已审查的清理 |
| `tests apply` | 优先处理测试信号，以及测试与代码相互支撑的簇 |
| `current branch apply` | 相对于实际合并基准清理当前工作 |
| `deep` | 对整个仓库进行只读审计 |
| `deep apply` | 在不重新设计架构的前提下清理整个仓库 |

只有 `apply` 才授权编辑。暂存、提交、推送、切换分支、重置和获取远程内容仍需另行授权。

## 工作流示例

从证据开始，而不是从编辑开始：

```text
$deslop deep

HIGH
- two fallback layers handle the same internal parse failure;
  current callers and history show no supported legacy input
- a local receipt is produced and verified by the same workflow;
  no external consumer or persisted trust boundary exists

PRESERVE
- a persisted readback detects truncated output across a write/read boundary
- a compatibility branch is required by a documented external protocol
```

审查每条证据链和保留决定。仅对有充分依据的范围执行应用：

```text
$deslop deep apply
```

以上示例仅为示意，不代表任何基准测试用例或性能声明。

## deslop 如何决策

- **独立证据根：** 当前需求、真实调用方、公开契约、协议、信任边界、持久化边界或科学不变量。
- **闭合论证循环：** 生产代码与测试不能仅凭彼此相互论证就成为必要内容。
- **生产代码／测试的不对称性：** 可以移除冗余测试证据，而不删除其观察的行为。
- **故障可见倾向：** 除非存在具体的恢复或转换契约，否则应让意外的内部故障显现出来。
- **删减而不重构：** 对依赖、抽象、包装层、兼容层及替代脚手架的默认预算为零。

完整决策模型请参阅[设计](docs/design.zh-CN.md)。自包含的运行时 [`SKILL.md`](skills/deslop/SKILL.md) 仍是 Agent 行为的权威依据。

## 安全模型

Codex 通过 [`allow_implicit_invocation: false`](skills/deslop/agents/openai.yaml) 强制要求明确调用。Claude Code 不读取这项 OpenAI 专用元数据；共享的标准兼容 frontmatter 则会指示 Claude 明确调用 `deslop`。Claude Code 仍可能根据描述选中此 Skill，但除非用户包含 `apply`，这种调用仍保持只读。默认模式与 `audit` 模式均为只读，可疑结构也可以记录为有意保留的决定。代码不能仅因看似具有防御性、由 Agent 编写，或拥有一项可以删除的测试，就被判定为可移除。

应用授权允许在范围内编辑，但不能将不确定性解释为支持删除。审查顺序请参阅[入门指南](docs/getting-started.zh-CN.md)，置信度类别和保留边界请参阅[设计](docs/design.zh-CN.md)。

## 证据

### 聚焦式开发评估

[`dev-v2-focused`](evals/dev-v2-focused/README.zh-CN.md) 通过成对的微型案例和三个端到端微型仓库，测试保留与简化决策。行为门槛先于缩减指标运行。微型案例与微型仓库的结果始终分开呈现，仓库不会发布项目级性能分数。

有关解读限制，请参阅[评估](docs/evaluation.zh-CN.md)；规范协议请参阅 [`evals/README.zh-CN.md`](evals/README.zh-CN.md)。

### 真实世界现场试验

| 案例 | 方法 | 状态 |
| --- | --- | --- |
| [`cluster-gpu-monitor`](evals/real-world/cluster-gpu-monitor/README.zh-CN.md) | 真实仓库；只读审计、人工裁定，再执行两批经审查的清理 | 已冻结的历史证据 |

首次现场试验通过公开的前后溯源记录了已接受的清理以及有意保留的决定。由于没有从同一冻结状态开展独立基线运行，它不属于受控 A/B 对比，也不能证明普遍优越性、100% 精确率或经生产环境验证的正确性。

未来可以添加更多案例，而不将其作为 Skill 调优输入；详情请参阅[现场试验](docs/field-trials.zh-CN.md)。

## 文档

| 文档 | 用途 |
| --- | --- |
| [文档索引](docs/README.zh-CN.md) | 选择用户、设计、证据或开发路径 |
| [入门指南](docs/getting-started.zh-CN.md) | 安装、调用模式、范围、更新和安全工作流 |
| [设计](docs/design.zh-CN.md) | 证据根、闭合循环、保留与删减原则 |
| [评估](docs/evaluation.zh-CN.md) | 聚焦式语料库、硬性门槛、运行规范和解读限制 |
| [现场试验](docs/field-trials.zh-CN.md) | 真实世界方法、溯源、隔离和案例登记表 |
| [开发](docs/development.zh-CN.md) | 仓库布局、验证、贡献和发布边界 |

## 仓库结构

```text
.claude-plugin/                 Claude Code Plugin and marketplace metadata
skills/deslop/                   Self-contained runtime Skill payload
docs/                            User, design, evidence, and development guides
evals/dev-v2-focused/            Active focused development evaluation
evals/real-world/                Manually adjudicated real-world evidence
evals/archive/                   Retired historical evaluation material
scripts/                         Validation and evaluation tooling
assets/                          README and project presentation assets
```

## 项目状态与贡献

公开版本从 v0.1.0 开始采用语义化版本控制。`0.x` 版本可以使用，但仍在演进；它不代表 `stable`、`production-ready` 或达到 1.0 品质。不可变的 Git 标签用于标识已发布的运行时与分发状态。基准测试候选版本保留各自独立的评估标签。

最有价值的贡献，是具有证据支持的案例，并附有位置相近的保留反例和独立行为判据，而不是一段只是看起来冗长的孤立代码。在提出 Skill 策略或评估变更前，请阅读[开发](docs/development.zh-CN.md)。

## 许可证

[MIT](LICENSE)
