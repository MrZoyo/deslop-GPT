# 开发

**简体中文** · [English](development.md)

本仓库明确区分 Skill 运行规则、当前评测、历史证据和项目展示材料。任何改动都不能模糊这些边界。

## 仓库布局

| 路径 | 职责 |
| --- | --- |
| [`.claude-plugin/`](../.claude-plugin/) | Claude Code Plugin 元数据与 GitHub 插件市场配置 |
| [`skills/deslop/`](../skills/deslop/) | 可独立使用的完整 Skill 运行时文件 |
| [`docs/`](./) | 面向用户和贡献者的使用、设计、证据与开发文档 |
| [`evals/dev-v2-focused/`](../evals/dev-v2-focused/) | 当前专项开发评测及其评分程序 |
| [`evals/dev-v3-evidence-edges/`](../evals/dev-v3-evidence-edges/) | 关于可达性、hermeticity、权威输入和 schema 边界的后续草案 |
| [`evals/runtime-controls/`](../evals/runtime-controls/) | 与清理质量分数分离的授权和宿主运行时控制案例 |
| [`evals/release-smoke/`](../evals/release-smoke/) | 明确记录限制、绑定具体版本的小型前向测试 |
| [`evals/real-world/`](../evals/real-world/) | 经人工复核并冻结留档的真实项目证据 |
| [`evals/archive/`](../evals/archive/) | 已退役的评测材料与历史诊断结果 |
| [`scripts/`](../scripts/) | 评测集校验、评测框架适配与结果导出工具 |
| [`assets/`](../assets/) | 用于项目展示的轻量资源 |
| [`.github/workflows/validate.yml`](../.github/workflows/validate.yml) | 与 CI 相同的仓库检查流程 |

## 变更边界

以下几部分应当分别维护：

- **运行时 Skill：** 供 Agent 执行的规则和参考资料。只改文档时，通常应保证这里逐字节不变。
- **当前评测：** 包括测试样例、清单、评分程序、校准样本、阈值和结果。项目展示方面的修改不能改变评测含义。
- **真实项目输入：** 公开源码树的精确副本。已冻结的快照绝不能顺手格式化、升级或清理。
- **参考证据：** 包括补丁和人工审核结论。评测期间必须对 Agent 隐藏，只有为了纠正客观的归档错误才可修改。
- **项目文档：** 负责解释和导航。可以概括其他部分，但必须链接到权威详情，不能另写一套相互冲突的规则。

## 验证

在仓库根目录运行以下命令，执行与 CI 相同的检查：

```bash
python3 scripts/validate_focused_corpus.py
python3 scripts/validate_evidence_edges_corpus.py

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill skills/deslop \
  --evals evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/mini-evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v3-evidence-edges/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/runtime-controls/evals.json
```

已退役的归档材料有单独的可选校验程序：

```bash
python3 scripts/validate_dev_v1_archive.py
```

这些命令检查目录结构，以及各校准样本是否呈现预期的通过或失败结果。它们不会实际运行 GPT 基准评测，也不能证明模型质量。

Claude Code 的发布配置需要另外使用其自带校验器检查：

```bash
claude plugin validate . --strict
```

如果要对命名空间命令做一次基本运行测试，可用 `claude --plugin-dir .` 加载本地仓库，再调用 `/deslop:deslop audit`。这一步会实际调用 Claude，不属于离线 CI 检查。

## 文档检查

对于仅涉及文档的变更：

1. 按 GitHub 兼容的 Markdown 渲染效果检查每个改动过的文件；
2. 从文档所在位置出发，验证本地链接和图片路径；
3. 确认动态徽章对应真实存在的工作流或仓库事实；
4. 确保 SVG 文件内容自包含、没有脚本，也不嵌入远程资源；
5. 搜索已经失效的路径，以及重复出现、可能彼此不一致的标准命令；
6. 检查文字是否暗示官方背书、使用不受控的对比，或作出没有证据的性能声明；
7. 修改发布指南时，同时校验 Claude Plugin 与插件市场元数据；
8. 对比改动前后受保护目录的 Git 树对象 ID。

不要只为了检查文档展示效果就引入一套庞大的 Markdown 工具；有针对性的本地链接检查已经足够。

## 贡献证据

最有价值的评测案例应当具备：

- 一个证据链已经查清的删除目标；
- 一个与之相近、但正确结论是保留的对照案例；
- 一套独立判断程序行为的标准；
- 一个会破坏行为的错误改法，或其他能证明“必须保留”检查确有意义的证据；
- 条件允许时，再提供一种不同但同样有效的清理方案；
- 评分不依赖某个历史补丁的具体代码结构。

如果当前项目中的可疑代码还缺少调用方、历史记录或约定方面的证据，就只能先放进审计候选列表，不能直接加入计分评测集。只有某种问题反复出现，而且误报边界已经弄清楚后，才应考虑新增 Skill 规则。

## 添加真实项目案例

请遵循[真实项目试用](field-trials.zh-CN.md)指南。使用 Git 自带机制准确导出公开源码树，严格分开 `input/` 与 `reference/`，记录人工决定保留的内容，并确认私有文件从未进入材料来源。提交真实项目案例时，不能暗中改变 Skill 运行规则或当前评测标准。

## 发布就绪条件

项目从 v0.1.0 起按语义化版本发布。`0.x` 版本已经可以使用，但仍在持续演进。带附注的 Git 标签一经发布便不再移动，用来唯一标识一个发布版本。发布 manifest 中的版本号必须与 Git 标签一致，只是不带开头的 `v`；Claude Plugin manifest 当前为 0.3.1，发布时必须创建对应的 v0.3.1 标签。Claude Code 以 manifest 版本号判断更新，所以每次修改 Plugin 都必须同时提升版本号和 marketplace 中固定的发布 ref。基准评测自身的修订标签与项目发布版本彼此独立。

在面向公众的发布提交之前：

- 运行与 CI 相同的检查；
- 对照改动前的 Git 树对象 ID，确认 `skills/`、当前评测和冻结输入没有意外变化；
- 检查完整 diff 和仓库状态；
- 对照 Codex 与 Claude Code 的最新官方文档，确认安装说明仍然准确；
- 没有明确标准和证据时，不要声称项目稳定、已被广泛采用、精确率很高或经过生产验证；
- 确保所有发布元数据与计划发布的 Git 标签一致。

不要从基准评测标签推断项目版本，也不要移动已经发布的版本标签。

## 发布方式兼容性说明

统一使用的 [`skills/deslop/`](../skills/deslop/) 目录遵循通用标准，各运行平台加载的都是完全相同的内容。Codex 可以从 `.agents/skills` 把它加载为独立 Skill；Claude Code 可以从 `.claude/skills` 加载同一目录，也可以通过本仓库的 Claude Plugin 加载。OpenAI 专用的 [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml) 负责 Codex 界面元数据，并要求用户明确调用该 Skill；Claude Code 会忽略这个文件。

Claude Code 的发布配置位于 [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) 和 [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json)。仓库根目录就是 Plugin 根目录，因此 Claude 会按默认规则扫描 `skills/<name>/SKILL.md`，并提供标准的命名空间命令 `/deslop:deslop`。manifest 声明的版本是 0.3.1，marketplace 也把 Plugin 源固定到对应的 `v0.3.1` 标签，不会在同一版本下把以后 `main` 的内容交给新用户。v0.3.1 保留 v0.3.0 的 test-first 范围，同时澄清授权与跨宿主行为。以后每次修改 Plugin，都必须同时提升 manifest 版本号和固定 ref。

Codex Plugin 的打包问题仍未解决，而且与 Claude Code 的发布方式无关。测试使用的是 Codex CLI 0.149.1。Plugin Creator 能通过一份临时的纯 Skills manifest，其中配置了 `skills: "./skills/"`；本地插件市场也能找到并安装它，缓存同样可以正常创建。缓存中确实存在 `skills/deslop/SKILL.md`，但在移除环境中另行安装的独立 Skill 后，新启动的 app-server 调用 `skills/list(forceReload=true)`，仍然没有返回已注册的 `deslop` Skill。因此，当前问题出在 Codex 没有把 Plugin 中的 Skill 注册到运行环境，而不是 `skills/deslop/` 目录结构有误，也不是独立 Skill 本身无效。Claude 专用的 `.claude-plugin/` 元数据不会改变这个结果，不能替代 Codex 当前支持的独立安装方式。
