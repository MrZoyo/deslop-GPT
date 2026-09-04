# 入门指南

**简体中文** · [English](getting-started.md)

`deslop` 默认只查看，不修改。第一次使用时，建议先审计一个较小的范围，再由人工检查结果；只有命令中明确带有 `apply`，才表示允许修改文件。

## 安装

### Codex：安装已发布的独立版 Skill（v0.3.2）

OpenAI 的 [Codex Skills 文档](https://developers.openai.com/codex/skills/)说明，`$skill-installer` 既可以安装推荐的 Skill，也可以从其他仓库下载安装。把本仓库的 Skill 地址交给它即可：

```text
$skill-installer
请从以下地址安装 Skill：
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.2/skills/deslop
```

v0.3.2 实际安装的内容只有 [`skills/deslop/`](../skills/deslop/)，不包括评测集和项目文档。这个目录遵循开放的 Agent Skills 结构，Claude Code 也可以直接加载。它保留 v0.3.1 的 test-first 规则，同时明确缺少局部证据时删除置信度的上限。v0.3.1、v0.3.0、v0.2.1 和 v0.1.0 的固定内容仍保留在各自标签下。

目前随 Codex 提供的 `$skill-installer` 会把下载的 Skill 放在安装器管理的目录中，默认是 `$CODEX_HOME/skills`（通常为 `~/.codex/skills`）。这只是安装器当前的实现方式，并不表示该路径是长期不变的公开约定。下文使用的 `$HOME/.agents/skills` 则是官方文档列出的用户级 Skill 加载目录，也便于直接检查其中内容。

### 用同一份本地源码供 Codex 和 Claude Code 加载

Codex 从 `$HOME/.agents/skills` 加载个人 Skill，Claude Code 使用 `$HOME/.claude/skills`。两者都支持指向 Skill 目录的符号链接。先把项目克隆到这两个加载目录之外，再按需创建链接：

```bash
git clone --branch v0.3.2 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

只创建当前平台需要的链接，并确认目标路径不存在后再执行对应的 `ln` 命令。Codex 通常会自动识别 Skill 的变更。Claude Code 会监视已经存在的 Skill 目录；如果顶层目录是在会话启动后才创建的，需要重启该会话。独立安装后，在 Codex 中使用 `$deslop`，在 Claude Code 中使用 `/deslop`。

这是一个独立的社区项目。能够在 OpenAI 或 Anthropic 的产品中运行，不代表它与这两家公司有关联，也不代表获得了官方认可。

### 从 GitHub 安装 Claude Code Plugin

仓库根目录同时可以作为 Claude Code Plugin 及其插件市场源。在 Claude Code 中添加这个 GitHub 仓库，然后安装其中的 `deslop`：

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

安装完成后，用标准的命名空间命令调用 Plugin：

```text
/deslop:deslop audit
```

插件市场目录跟随 `main`，声明的 Plugin 版本是 0.3.2，并使用明确的 HTTPS Git source，同时固定到对应的 v0.3.2 标签和发布提交 `0cc15c036b07691c600bda1219b8cc5c197ca3f1`。这样既不会依赖用户的 GitHub SSH 传输设置，也能保证 `main` 以后出现开发中改动时，新安装用户仍得到正式发布内容。Claude Code 依靠 manifest 中的版本号判断更新，因此以后每次修改 Plugin，都必须提升版本号，并把目录 pin 移到新的发布。

在本地开发 Plugin 时，可以从本仓库启动 Claude Code：

```bash
claude --plugin-dir .
```

这样无需安装，就能以 `/deslop:deslop` 命令加载同一个 [`skills/deslop/`](../skills/deslop/) 目录。

### 从 v0.3.1 升级

v0.3.2 更新了 Skill 运行规则，但 `skills/deslop/` 路径没有变化。如果符号链接指向本地源码仓库，只需把该仓库切换到 v0.3.2 标签，链接本身不用改。通过 Codex 安装器下载的副本，应使用上方的 v0.3.2 地址重新安装。已经安装 Claude Code Plugin 的用户可运行 `claude plugin update deslop@deslop`，然后重启 Claude Code。v0.3.1 或更早版本都可以用同样方式直接升级。

### 从 v0.1.0 升级

安装器不会自动适配 Git 仓库中的目录改名，因此需要从新地址重新安装：

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.2/skills/deslop
```

旧的 v0.1.0 路径为：

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop
```

如果 Codex 通过符号链接加载本地源码仓库，请先检查现有链接：

```bash
test -L "$HOME/.agents/skills/deslop"
readlink "$HOME/.agents/skills/deslop"
```

只有当输出确认它确实是 v0.1.0 的符号链接，并且指向预期的 `~/.local/share/deslop-GPT/skill/deslop` 时，才删除链接本身，然后为 v0.3.2 重新创建链接：

```bash
unlink "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" \
  "$HOME/.agents/skills/deslop"
```

如果该路径是一个真实目录，或链接指向其他位置，请先停下来查清楚，不要直接删除。v0.1.0 仍作为固定的历史版本保留在原标签路径中。

### 开发分支

[`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) 可能包含尚未发布的改动。只有明确想使用开发版时才选择它；如果需要稳定复现，请使用带 v0.3.2 标签的地址。

独立版 Skill 的目录也随仓库版本变化：v0.1.0 位于 `skill/deslop/`，从 v0.2.0 开始则统一使用 `skills/deslop/`。

### 发布方式现状

Claude Code 的 Plugin 配置由 [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) 定义，[`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) 则提供从 GitHub 安装所需的插件市场信息。这些文件只供 Claude Code 使用，不能替代 Codex 加载独立 Skill 的方式。

v0.3.2 继续使用带版本标签的独立 Skill 作为 Codex 发布方式。OpenAI 当前文档也支持通过 Plugin 分发 Skill，但本仓库尚未提供 Codex Plugin 元数据。早期 Codex CLI 0.149.1 的注册实验只作为历史开发证据保留，不能用来描述当前 Codex 平台的支持情况。

## 调用模式

根据当前使用的平台和安装方式选择命令：

| 平台与安装方式 | 命令名称 |
| --- | --- |
| Codex 独立 Skill | `$deslop` |
| Claude Code 独立 Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

在该命令名称后追加以下参数：

| 参数 | 授权与范围 |
| --- | --- |
| 不带参数 | 对已经确定的范围做只读审计 |
| `audit` | 明确要求只读审计 |
| `apply` | 修改已经确定的范围内的文件 |
| `tests` | 重点审查测试是否提供了有效证据，仍为只读 |
| `tests apply` | 执行以测试为重点的清理，包括证据充分、只会相互自证的测试与代码组 |
| `current branch apply` | 以实际的合并基点为准，清理当前分支上的工作 |
| `deep` | 对整个仓库做只读审计 |
| `deep apply` | 清理整个仓库，但不重新设计架构 |
| `path/to/file audit` | 只检查指定路径，以及判断相关约定所必需的最少上下文 |

只有 `apply` 表示允许编辑。拉取远程内容、重置、切换分支、暂存、提交、推送和创建备份仍需用户另行授权。

在只读模式中，如果工具支持，应使用禁止写入的选项，或把缓存和生成输出重定向到临时位置。如果工具仍留下临时缓存，审计结果应明确披露；如果某项检查无法避免改动仓库拥有的内容，就不要运行，并说明原因。

Codex 通过 [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml) 要求用户明确调用这个 Skill；该文件只对 OpenAI 的运行环境生效。Claude Code 读取通用格式的 `SKILL.md`，可能根据其中的描述自动选用该 Skill；但只要没有 `apply`，操作仍然是只读的。需要确保每次都以同样方式调用时，请明确输入 `/deslop` 或 `/deslop:deslop`。

## 如何确定操作范围

### 指定路径

指定路径可以把审查范围控制到最小：

```text
$deslop src/reporting.py tests/test_reporting.py audit
```

为了判断证据是否独立，Agent 可以查看最低限度的调用方、约定、历史记录和测试。进入 `apply` 模式后，修改仍限于指定路径；只有在必须同步调整相邻文件中的一小处约定时才可例外。

### 当前工作

在 Git 仓库中，`current branch` 或省略范围，都表示审查当前工作相对于本地实际合并基点的变化。已暂存、未暂存和未跟踪的内容都包含在内；Skill 不会擅自假定基准分支是 `main`。

### 整个仓库

`deep` 只扩大检查范围，不会扩大操作权限。即使使用 `deep apply`，生成代码、随项目复制进来的依赖、第三方源码、迁移历史、锁文件和外部生成的快照也默认排除；只有用户明确纳入，或有证据表明它确实由本仓库维护时，才会处理。

## 先审查后操作的工作流

1. 阅读仓库说明，并检查 `git status`。
2. 使用当前平台对应的 `deslop` 命令，从 `audit`、指定路径或 `deep` 开始。
3. 检查每个候选项的外部证据和置信度，并确认哪些边界必须保留。
4. 执行任何修改之前，先解决所有 MEDIUM 项的不确定性。
5. 只对证据充分的范围调用 `apply`。
6. 先运行仓库已有的针对性检查，再运行文档规定的最终验证。
7. 查看最终差异。暂存、提交或推送都必须另外获得授权。

审计结果应清楚区分“可以删除的候选项”和“必须保留的系统边界”，不能只列一份未经判断的代码异味清单。

```text
HIGH
- 内部校验器重复多余；产出方和校验方使用完全相同的输入

PRESERVE
- 写入后回读跨越了真实的读写故障边界

UNRESOLVED
- 兼容分支有真实调用方，但目前不清楚它承诺支持哪些版本
```

确认完整证据链后，只执行 HIGH 项；其余内容应当保留或继续调查。

## 更新与移除

如果通过符号链接固定在某个版本，请先审查新版，再把本地仓库切换到新版的固定标签；链接本身不用改。如果通过 `$skill-installer` 安装，请用新版的标签地址再次调用安装器，并按当前提示完成更新。要移除独立 Skill，只删除实际安装位置中由安装器管理的 `deslop` 目录，或对应的 `deslop` 符号链接。另行保存的源码仓库是否删除，可按自己的工作方式决定。

如果安装的是 Claude Code Plugin，刷新插件市场后可用 `/plugin update deslop@deslop` 更新，或用 `/plugin uninstall deslop@deslop` 卸载。卸载 Plugin 不会删除另外创建的独立 Skill 链接。

## 后续步骤

- 阅读[设计](design.zh-CN.md)，了解如何判断证据是否充分。
- 解读开发评测结果前，先阅读[评测](evaluation.zh-CN.md)。
- 阅读[真实项目试用](field-trials.zh-CN.md)，了解真实项目证据的适用边界。
