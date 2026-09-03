<p align="center">
  <img src="assets/deslop-banner.svg" alt="deslop — 专为 Agent 维护的代码库设计，优先做减法的清理工具" width="100%">
</p>

<h1 align="center">deslop</h1>

<p align="center">
  <strong>专为 Agent 维护的代码库设计，优先做减法的 Agent Skill</strong>
</p>

<p align="center"><strong>简体中文</strong> · <a href="README.md">English</a></p>

<p align="center">
  以证据为依据，清除层层堆积的机制，同时保留真正需要的行为。
</p>

<p align="center">
  <a href="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml"><img src="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml/badge.svg" alt="仓库检查工作流"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f.svg?style=flat-square" alt="MIT 许可证"></a>
  <a href="skills/deslop/"><img src="https://img.shields.io/badge/Agent%20Skill-Codex%20%2B%20Claude%20Code-0969da.svg?style=flat-square" alt="兼容 Codex 和 Claude Code 的 Agent Skill"></a>
  <a href="#安全模型"><img src="https://img.shields.io/badge/default-read--only-6e7781.svg?style=flat-square" alt="默认只读"></a>
  <a href="evals/real-world/cluster-gpu-monitor/README.zh-CN.md"><img src="https://img.shields.io/badge/field%20trial-manually%20adjudicated-8250df.svg?style=flat-square" alt="经人工复核的真实项目试用"></a>
</p>

`deslop` 用来审计代码库；用户明确授权后，它还可以清理由编程 Agent 在多轮实现和修正中积累的复杂代码。反复迭代常会留下彼此重叠的回归测试、由同一套逻辑产出结果再自行验证的检查，以及不按现行约定处理错误、反而把错误藏起来的回退层。

它做的是不改变必要行为的代码减法，不是美化源码。`deslop` 不是格式化工具，不负责把代码改得“更像人写的”，不追求测试越少越好，也不主张一律删除防御性代码，更不会自行取得仓库编辑权限。它会沿着每条理由追查独立证据；只要某项行为仍有明确约定，或证据尚不足以判断，就会选择保留。

> **要精简的是测试，不是程序支持的行为。**

## 目标对象

以下比例表示设计上的处理优先级，不代表这些问题在真实项目中的出现频率。

| 优先级 | 目标 | 判断问题 |
| ---: | --- | --- |
| ~50% | **测试膨胀** | 每项测试是否都用独立判断依据保护了一个有当前 owner 的独立失败域？ |
| ~25% | **形式大于实效的验证** | 校验方能否发现产出方自身发现不了的错误，还是双方使用相同信息、也会因相同原因一起出错？ |
| ~25% | **过度防御与回退逻辑** | 恢复路径是否履行一项当前仍有效的约定，还是只把意外的内部错误藏起来？ |

普通死代码、包装层、抽象和注释只是次要目标。只有它们属于上述某类成组问题，或存在直接且把握很高的删除证据时，才会处理。

## 做减法，保留行为

| 移除 | 保留 |
| --- | --- |
| 只能为自身找理由，或彼此重复的测试 | 不同的成功、拒绝、报错和边界行为 |
| 没有独立使用者的校验和、回执或校验器 | 真正跨越读写故障边界的持久化数据回读与损坏检测 |
| 凭空猜测或已经过时的回退链 | 仍受支持的兼容行为和文档明确规定的协议行为 |
| 可信调用链内部层层重复的防御检查 | 在外部输入和不可信边界上确实需要的处理 |
| 没有独立用途的包装层与配套测试 | 安全、事务、并发、资源约束和科学不变量 |

看起来像某种代码异味，只能作为调查线索，不能直接下结论。证据不足时，安全与信任边界、仍受支持的调用方、持久化格式和数值约束都默认保留。

## 快速开始

### Codex：安装独立版 Skill（v0.3.1）

把下面的 GitHub Skill 地址交给内置安装器：

```text
$skill-installer
请从以下地址安装 Skill：
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.1/skills/deslop
```

如果希望直接检查本地源码，可以把 Skill 运行目录链接到 Codex 官方文档规定的用户级 Skill 目录：

```bash
git clone --branch v0.3.1 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
```

Codex 支持通过符号链接加载 Skill 目录，并会自动识别其中的改动。带 v0.3.1 标签的地址固定指向当前发布的独立版 Skill；[`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) 是开发分支，可能包含尚未发布的内容。

### Claude Code：从 GitHub 安装 Plugin

在 Claude Code 中，把本仓库添加为插件市场源，然后安装 Plugin：

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

Plugin 的标准命令是 `/deslop:deslop`。如果使用本地源码仓库，可在仓库根目录运行 `claude --plugin-dir .` 直接加载。插件市场目录从 `main` 读取，但 Plugin 源使用明确的 HTTPS Git URL，并固定到 v0.3.1 标签及其发布提交。这个补丁版本澄清需求证据与宿主指令文件，加入当前只读控制案例，并让评测 wrapper 识别不同宿主。v0.3.0 的 test-first 与 evidence-edge 范围保持不变。

### 一份本地源码，同时供两个平台加载

同一份已发布的 Skill 目录可以分别链接到两个平台的用户级加载目录：

```bash
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

只创建当前平台需要的链接，并确认目标路径不存在后再执行对应的 `ln` 命令。Claude Code 独立加载的 Skill 使用 `/deslop` 调用。安装位置、从 v0.1.0 升级、更新、卸载，以及更稳妥的“先审查、后修改”流程，详见[入门指南](docs/getting-started.zh-CN.md)。`deslop` 是独立社区项目，不是 OpenAI 或 Anthropic 的产品。

### 发布方式现状

共用的 [`skills/deslop/`](skills/deslop/) 目录遵循开放的 Agent Skills 结构，Codex 和 Claude Code 加载的内容完全相同。[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) 与 [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) 提供 Claude Code 所需的 Plugin 配置。目前仍不发布 Codex Plugin：测试环境虽然能安装并缓存纯 Skills Plugin，却没有把其中的 Skill 注册到 Codex。Codex 的独立安装方式不受影响。详情见[发布方式兼容性说明](docs/development.zh-CN.md#发布方式兼容性说明)。

### 明确调用

| 平台与安装方式 | 命令名称 |
| --- | --- |
| Codex 独立 Skill | `$deslop` |
| Claude Code 独立 Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

无论使用哪个平台，都可以在相应命令后追加同样的模式与范围参数：

| 参数 | 效果 |
| --- | --- |
| 不带参数 | 对已经确定的范围做只读审计 |
| `audit` | 明确要求只读审计 |
| `apply` | 在既定范围内执行已经审查过的清理 |
| `tests apply` | 优先精简冗余测试，以及只会相互自证的测试与代码组 |
| `current branch apply` | 以实际合并基点为准，清理当前分支上的工作 |
| `deep` | 对整个仓库做只读审计 |
| `deep apply` | 清理整个仓库，但不重新设计架构 |

只有 `apply` 表示允许编辑。暂存、提交、推送、切换分支、重置和拉取远程内容仍需另行授权。

## 工作流示例

先查证据，不要一上来就改代码：

```text
$deslop deep

HIGH
- 两层回退逻辑处理的是同一个内部解析错误；
  当前调用方和历史记录都表明没有需要兼容的旧输入
- 同一套流程既生成本地回执，又自行验证回执；
  不存在外部使用者，也没有跨越持久化信任边界

PRESERVE
- 写入后回读可以跨越读写边界，发现输出被截断
- 有文档记录的外部协议明确要求保留一条兼容分支
```

逐条检查证据链，以及决定保留的边界。只对证据充分的范围执行清理：

```text
$deslop deep apply
```

以上只是用法示意，不代表任何基准评测案例，也不构成性能声明。

## deslop 如何决策

- **独立证据来源：** 当前需求、真实调用方、公开约定、协议、信任边界、持久化边界或科学不变量。
- **相互自证的闭环：** 生产代码和测试不能只靠彼此证明对方有必要存在。
- **生产可达性与路径闭合：** 应证明当前输入能够穿过完整路径抵达 consumer，而不是只看孤立 caller 或测试注入的分支。
- **生产代码与测试并不对等：** 冗余测试可以删除，但测试所观察的行为不能因此一并删除。
- **优先暴露错误：** 除非存在明确的恢复或错误转换约定，否则意外的内部错误应当直接暴露。
- **只做减法，不重新设计：** 默认不新增依赖、抽象层、包装层、兼容层或替代脚手架。

完整的判断方法见[设计](docs/design.zh-CN.md)。Agent 实际执行时，仍以独立完整的 [`SKILL.md`](skills/deslop/SKILL.md) 为准。

## 安全模型

Codex 通过 [`allow_implicit_invocation: false`](skills/deslop/agents/openai.yaml) 要求用户明确调用这个 Skill。Claude Code 不读取这项 OpenAI 专用元数据；共用 `SKILL.md` 文件头中的通用元数据则说明 `deslop` 应由用户明确调用。Claude Code 仍有可能根据描述自动选中该 Skill，但只要用户没有写 `apply`，它就只能读取和审计。默认模式与 `audit` 都是只读模式；审计也可以明确记录某段可疑代码经查证后决定保留。不能仅仅因为代码看起来很防御、由 Agent 编写，或有一项可以删除的测试，就认定代码本身也可以删除。

只读验证应尽量重定向缓存或生成输出，并披露偶然留下的残留物。`apply` 只授权在既定范围内编辑，不能把尚未查清的问题一律解释成可以删除。审查顺序见[入门指南](docs/getting-started.zh-CN.md)，置信度分级和默认保留的边界见[设计](docs/design.zh-CN.md)。

## 证据

### 验证状态

| Skill payload | 宿主与加载方式 | 运行次数 | 能够说明什么 |
| --- | --- | --- | --- |
| v0.3.1 发布内容（发布前精确哈希） | Codex 子代理按路径加载 Skill | 1 次默认 audit，加 `t02b`、`t03b` 两个保留案例 | 窄范围开发回归 smoke；三次都没有改变 fixture 内容 |
| v0.3.1 标签 Plugin | Claude Code 2.1.259，隔离配置与远端 `main` catalog | 1 次 marketplace 安装，不调用模型 | 远程 HTTPS source 把 v0.3.1 标签解析到提交 `a19128d`；安装版本和运行时哈希一致 |
| v0.3.0 正式版精确哈希 | Codex 子代理按路径加载 Skill | 3 个小型仓库 apply，加 1 次 audit | 三个清理结果均通过隐藏行为、精简和新增内容限制；不包含 CLI discovery 或 baseline 证据 |
| v0.3.0 正式版精确哈希 | Claude Code 2.1.259 本地 Plugin，Haiku 4.5 | 1 次 audit，加 1 次 apply | 已验证 Plugin 加载和一个有效清理结果；apply 在最终报告前达到回合上限 |
| 更早的开发 payload | Codex CLI 0.149.1，`gpt-5.6-sol` | rc3 小案例、rc4 小型仓库和 rc5 定向诊断 | 只适用于对应 payload 哈希的历史开发证据 |

2026-09-03 的两组前向 smoke 保存在 [`evals/release-smoke/`](evals/release-smoke/) 下。它们都是已暴露、单次、没有 baseline 的开发诊断，不是 held-out 模型效果证据。旧版 rc3 小案例试运行中，加载当时的 Skill 后总 token 增加 63.1%，耗时增加 16.5%；这次单次结果不能预测 v0.3.x 成本，但说明 `deslop` 更适合有意安排的累积清理，不适合作为每个微小 diff 的固定步骤。

### 专项开发评测

[`dev-v2-focused`](evals/dev-v2-focused/README.zh-CN.md) 使用成对的小案例和三个端到端小型仓库，检查 Agent 是否能正确判断该删什么、该留什么。只有先通过行为检查，才会计算精简指标。小案例和小型仓库的结果始终分开报告，本仓库不发布项目级性能分数。

后续的 [`dev-v3-evidence-edges`](evals/dev-v3-evidence-edges/README.zh-CN.md) 草案收录了 19 条匿名化现场观察，并先实现了 7 对新的可执行案例。目前只校验草案内部一致性，不把它描述成模型表现证据。

结果应如何解读，见[评测](docs/evaluation.zh-CN.md)；完整规则见 [`evals/README.zh-CN.md`](evals/README.zh-CN.md)。

### 真实项目试用

| 案例 | 方法 | 状态 |
| --- | --- | --- |
| [`cluster-gpu-monitor`](evals/real-world/cluster-gpu-monitor/README.zh-CN.md) | 真实仓库；先做只读审计和人工复核，再分两批执行经审核的清理 | 已冻结的历史证据 |

第一个真实项目案例用公开的清理前后提交记录，保存了获准执行的改动，也保存了明确决定不改的内容。由于没有从完全相同的初始状态独立运行基线，它不属于受控 A/B 对比，不能证明普遍优于其他方案、达到 100% 精确率，或已经过生产环境验证。

以后可以继续添加案例，但不能直接把案例当作 Skill 调优输入；详见[真实项目试用](docs/field-trials.zh-CN.md)。

## 文档

| 文档 | 用途 |
| --- | --- |
| [文档索引](docs/README.zh-CN.md) | 按使用、设计、证据或开发目的选择文档 |
| [入门指南](docs/getting-started.zh-CN.md) | 安装、调用模式、作用范围、更新与安全使用流程 |
| [设计](docs/design.zh-CN.md) | 独立证据、相互自证、默认保留边界与减法原则 |
| [评测](docs/evaluation.zh-CN.md) | 专项评测集、硬性检查、运行要求与解读限制 |
| [真实项目试用](docs/field-trials.zh-CN.md) | 真实案例的记录方法、来源、隔离要求与案例列表 |
| [开发](docs/development.zh-CN.md) | 仓库结构、检查命令、贡献方式与发布边界 |

## 仓库结构

```text
.claude-plugin/                 Claude Code Plugin 与插件市场元数据
skills/deslop/                  可独立使用的完整 Skill 运行时文件
docs/                           使用、设计、证据与开发指南
evals/dev-v2-focused/           当前专项开发评测
evals/dev-v3-evidence-edges/    后续证据边界草案
evals/runtime-controls/         授权与宿主运行时控制案例
evals/release-smoke/            绑定版本的前向 smoke 记录
evals/real-world/               经人工复核的真实项目证据
evals/archive/                  已退役的历史评测材料
scripts/                        仓库校验与评测工具
assets/                         README 与项目展示资源
```

## 项目状态与贡献

项目从 v0.1.0 起按语义化版本发布。`0.x` 版本已经可以使用，但仍在持续演进；这不代表项目已经“稳定”“可直接用于生产”，或达到了 1.0 的成熟度。发布后不再移动的 Git 标签用来固定 Skill 运行内容和发布配置。基准评测候选版使用各自独立的评测标签。

最有价值的贡献不是一段孤立、只是看起来很啰嗦的代码，而是证据充分的案例：旁边有一个相近但应当保留的对照案例，并且有独立标准可以判断程序行为。在提出新的 Skill 规则或修改评测前，请先阅读[开发](docs/development.zh-CN.md)。

## 许可证

[MIT](LICENSE)
