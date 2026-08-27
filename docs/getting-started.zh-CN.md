# 入门指南

**简体中文** · [English](getting-started.md)

`deslop` 默认为只读。安全的首次使用方式是先对较小范围执行审计，再由人工审查；只有包含 `apply` 的调用才授权编辑文件。

## 安装

### Codex：已发布的独立 Skill v0.2.1

OpenAI 的 [Codex Skills 文档](https://developers.openai.com/codex/skills/)说明，可以使用 `$skill-installer` 安装精选 Skill 以及来自其他仓库的 Skill。请使用本仓库 URL 调用它：

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/v0.2.1/skills/deslop
```

v0.2.1 的可安装载荷仅为 [`skills/deslop/`](../skills/deslop/)，不包括评估语料库或项目文档。同一载荷遵循开放的 Agent Skills 结构，也可以由 Claude Code 直接发现。运行时载荷与 v0.2.0 保持不变；v0.2.1 新增 Claude Code 分发元数据和双语项目文档。不可变的 v0.1.0 载荷仍位于 [`skill/deslop/`](https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop)。

当前内置的 `$skill-installer` 会在由安装器管理的位置管理已下载的 Skill，默认位于 `$CODEX_HOME/skills` 下（通常是 `~/.codex/skills`）。这是安装器当前的行为，而非永久的公开路径契约。下文的 `$HOME/.agents/skills` 是有文档记录、可直接审查的用户发现路径。

### 供 Codex 与 Claude Code 使用的可审查独立检出

Codex 在 `$HOME/.agents/skills` 下发现个人 Skill；Claude Code 使用 `$HOME/.claude/skills`。二者都支持以符号链接方式安装的 Skill 目录。将项目克隆到这两个发现目录之外，然后只创建你需要的链接：

```bash
git clone --branch v0.2.1 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

只需为你使用的宿主创建对应链接。仅当目标不存在时才运行相应的 `ln` 命令。Codex 通常会自动检测 Skill 变更。Claude Code 会监视已有的 Skill 目录；但如果顶层目录是在会话启动后才创建的，请重启该会话。独立 Skill 在 Codex 中的命令名称是 `$deslop`，在 Claude Code 中则是 `/deslop`。

这是一个独立的社区 Skill。兼容性并不表示与 OpenAI 或 Anthropic 存在关联或获得其背书。

### 从 GitHub 安装 Claude Code Plugin

仓库根目录同时也是 Claude Code Plugin 和 marketplace。在 Claude Code 中添加该 GitHub 仓库，并安装其中的 `deslop` 条目：

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

使用其规范的带命名空间命令调用已安装的 Plugin：

```text
/deslop:deslop audit
```

marketplace 跟踪 `main`，并声明了 0.2.1 版 Plugin。对应的 v0.2.1 标签包含同一份 Claude Plugin 元数据，并固定了该版本。由于 Claude Code 将清单版本作为更新键，未来的 Plugin 变更必须先递增该版本，已安装的用户才能收到更新。

进行本地 Plugin 开发时，请从本仓库启动 Claude Code：

```bash
claude --plugin-dir .
```

这样无需安装，即可在 `/deslop:deslop` 命名空间下加载同一个 [`skills/deslop/`](../skills/deslop/) 载荷。

### 从 v0.2.0 升级

运行时 Skill 载荷及其 `skills/deslop/` 路径均未变化。通过符号链接安装的源码检出只需切换到 v0.2.1 标签，链接本身无需修改。由安装器管理的 Codex 副本应使用上方的 v0.2.1 URL 重新安装。Claude Code Plugin 安装方式从 v0.2.1 开始提供，请使用上方的 marketplace 命令。

### 从 v0.1.0 升级

安装器不会自动跟随 Git 目录重命名。请从以下位置重新安装：

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.2.1/skills/deslop
```

旧的 v0.1.0 路径为：

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop
```

如果 Codex 链接的是源码检出，请先检查现有目标：

```bash
test -L "$HOME/.agents/skills/deslop"
readlink "$HOME/.agents/skills/deslop"
```

只有当输出确认它是预期指向 `~/.local/share/deslop-GPT/skill/deslop` 的 v0.1.0 符号链接时，才移除该符号链接本身，并为 v0.2.1 重新创建：

```bash
unlink "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" \
  "$HOME/.agents/skills/deslop"
```

如果目标是实际目录或指向其他位置，请停止操作并检查，而不要移除它。v0.1.0 作为不可变历史版本，仍在其原始标签路径上受到支持。

### 开发分支

[`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) 路径可能包含尚未发布的变更。只有在你有意使用开发版本时才选择它；需要可复现性时，请使用带标签的 v0.2.1 路径。

独立运行时路径随仓库一起版本化：v0.1.0 仍位于 `skill/deslop/`，而 v0.2.0 及更高版本使用规范路径 `skills/deslop/`。

### 分发状态

Claude Code 打包由 [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) 定义，GitHub 安装目录则是 [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json)。这些文件仅供 Claude 使用，不能替代 Codex 的独立发现方式。

Codex Plugin 分发仍暂不提供。在经测试的 Codex CLI 0.149.1 环境中，Plugin 安装与缓存成功，但其中捆绑的 Skill 未能完成原生注册。上文带标签的独立路径仍是受支持的 Codex 发布路径。

## 调用模式

根据当前宿主与分发方式选择命令名称：

| 宿主与分发方式 | 命令名称 |
| --- | --- |
| Codex 独立 Skill | `$deslop` |
| Claude Code 独立 Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

在该命令名称后追加以下参数：

| 参数 | 授权与范围 |
| --- | --- |
| 无 | 对既定范围进行只读审计 |
| `audit` | 明确进行只读审计 |
| `apply` | 修改既定范围内的文件 |
| `tests` | 以测试信号为重点进行只读审计 |
| `tests apply` | 应用以测试为重点的清理，包括有充分依据的相互支撑簇 |
| `current branch apply` | 相对于实际合并基准对当前工作应用清理 |
| `deep` | 对整个仓库进行只读审计 |
| `deep apply` | 在不重新设计架构的前提下清理整个仓库 |
| `path/to/file audit` | 将检查限制在明确路径及最少必要的契约上下文内 |

只有 `apply` 才授权编辑。除非另行请求，否则它不授权获取远程内容、重置、切换分支、暂存、提交、推送或创建备份。

Codex 通过 [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml) 强制仅限明确选择。该文件是 OpenAI 专用的。Claude Code 会读取共享的标准兼容 `SKILL.md`，并可能根据其描述选中该 Skill；如果没有 `apply`，这种选择仍为只读。需要可复现调用时，请明确使用 `/deslop` 或 `/deslop:deslop`。

## 范围行为

### 明确路径

使用路径获得最小审查表面：

```text
$deslop src/reporting.py tests/test_reporting.py audit
```

Agent 可以检查判断证据是否独立所需的最少调用方、契约、历史和测试。在应用模式下，除非直接需要少量相邻契约变更，否则操作范围不会超出指定路径。

### 当前工作

在 Git 中，`current branch` 或省略范围表示相对于实际本地合并基准的当前工作。已暂存、未暂存和未跟踪的工作均属于该边界；绝不自动假定 `main`。

### 整个仓库

`deep` 扩大检查范围，而不扩大权限。在 `deep apply` 中，生成代码、供应商依赖、第三方源码树、迁移、锁文件和外部生成的快照仍被排除，除非明确纳入或能够证明归仓库所有。

## 先审查后操作的工作流

1. 阅读仓库指令并检查 `git status`。
2. 从宿主的 `deslop` 命令配合 `audit`、明确路径或 `deep` 开始。
3. 审查每个候选项的外部证据、置信度和保留决定。
4. 应用任何内容之前，先解决 MEDIUM 级别的不确定性。
5. 仅对有充分依据的范围调用 `apply`。
6. 先运行仓库已有的针对性检查，再运行有文档记录的最终验证。
7. 检查最终差异。暂存、提交或推送只能作为另行授权的操作执行。

审计应区分候选项与边界，而不是生成一份原始的代码异味列表。

```text
HIGH
- redundant internal verifier; producer and verifier share all inputs

PRESERVE
- persisted readback crosses a real write/read failure boundary

UNRESOLVED
- compatibility branch has a caller, but its supported-version contract is unclear
```

确认其证据链后，仅应用 HIGH 级别的发现。保留或进一步调查其他项目。

## 更新与移除

对于固定版本的符号链接安装，请审查较新版本并检出其不可变标签；链接本身无需改变。如果通过 `$skill-installer` 安装，请用更新的带标签 URL 再次调用，并遵循其当前更新提示。要移除独立 Skill，只需从安装位置移除由安装器管理或以符号链接方式安装的 `deslop` 目录；是否保留单独的源码检出，由你自己的工作流决定。

对于 Claude Code Plugin 安装，在刷新 marketplace 后使用 `/plugin update deslop@deslop` 更新，或使用 `/plugin uninstall deslop@deslop` 移除。移除 Plugin 不会同时移除单独的独立 Skill 链接。

## 后续步骤

- 阅读[设计](design.zh-CN.md)，了解证据模型。
- 在解读开发结果之前阅读[评估](evaluation.zh-CN.md)。
- 阅读[现场试验](field-trials.zh-CN.md)，了解真实世界证据边界。
