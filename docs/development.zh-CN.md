# 开发

**简体中文** · [English](development.md)

本仓库将运行时策略、活跃评估、历史证据和展示材料彼此分离。每项变更都应清晰体现这些边界。

## 仓库布局

| 路径 | 职责 |
| --- | --- |
| [`.claude-plugin/`](../.claude-plugin/) | Claude Code Plugin 身份信息与 GitHub marketplace 目录 |
| [`skills/deslop/`](../skills/deslop/) | 自包含的运行时 Skill 载荷 |
| [`docs/`](./) | 用户、设计、证据和贡献者文档 |
| [`evals/dev-v2-focused/`](../evals/dev-v2-focused/) | 活跃的聚焦式开发评估与评分器 |
| [`evals/real-world/`](../evals/real-world/) | 经人工裁定、已冻结的真实世界证据 |
| [`evals/archive/`](../evals/archive/) | 已停用的评估材料与历史诊断信息 |
| [`scripts/`](../scripts/) | 语料库验证、测试工具包装与结果导出工具 |
| [`assets/`](../assets/) | 轻量级仓库展示资源 |
| [`.github/workflows/validate.yml`](../.github/workflows/validate.yml) | 等同 CI 的仓库验证 |

## 变更边界

将以下内容视为彼此独立的产品：

- **运行时 Skill：** 面向 Agent 的策略与参考资料。文档工作通常应使其逐字节保持不变。
- **活跃评估：** 测试夹具、清单、评分器、校准、阈值和结果。展示工作不得改变其语义。
- **真实世界输入：** 精确的公开源码树。绝不格式化、现代化或清理已冻结的快照。
- **参考证据：** 补丁与裁定。对任何接受评估的 Agent 隐藏这些内容，并且仅在纠正客观的归档错误时修改。
- **项目文档：** 解释性文字与导航。可以概述其他层，但必须链接到其规范详情，而不能创造相互竞争的事实来源。

## 验证

从仓库根目录运行等同 CI 的检查：

```bash
python3 scripts/validate_focused_corpus.py

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
```

已停用的归档拥有单独的可选验证器：

```bash
python3 scripts/validate_dev_v1_archive.py
```

这些命令验证结构与已知的行为极性。它们不会运行 GPT 基准测试，也不能证明模型质量。

请另行使用宿主验证器验证 Claude Code 分发：

```bash
claude plugin validate . --strict
```

若要进行带命名空间的运行时冒烟测试，请通过 `claude --plugin-dir .` 加载检出并调用 `/deslop:deslop audit`。该操作会调用 Claude，不属于离线的等同 CI 检查。

## 文档质量保证

对于仅涉及文档的变更：

1. 按照与 GitHub 兼容的渲染假设检查每个已变更的 Markdown 文件；
2. 验证本地链接与图片目标相对于其源文件的路径；
3. 验证动态徽章指向真实的工作流或仓库事实；
4. 保持 SVG 资源自包含、无脚本且不嵌入远程内容；
5. 搜索过时路径与重复的规范命令；
6. 审查声明中是否暗示背书、使用不受控比较或缺乏依据的性能措辞；
7. 分发指南变更时，验证 Claude Plugin 与 marketplace 元数据；
8. 对比变更前后受保护 Git 树的身份标识。

不要仅为展示质量保证而加入大型 Markdown 框架；有针对性的本地链接检查已经足够。

## 贡献证据

最有价值的评估贡献应包含：

- 一项具有已解析证据链的删除目标；
- 一个位置相近的保留反例；
- 一个独立行为判据；
- 一个破坏性变体或其他能够证明保留门槛确有意义的证据；
- 在可行时提供另一种有效清理方案；
- 不依赖某个历史补丁的具体形态。

缺乏调用方、历史或契约证据的当前项目异味应进入审计候选池，而不是直接进入计分语料库。在某种模式重复出现且其误报边界得到理解之前，不要提出新的 Skill 规则。

## 添加现场试验

请遵循[现场试验](field-trials.zh-CN.md)指南。使用 Git 原生机制捕获精确的公开源码树，将 `input/` 与 `reference/` 分开，记录人工保留决定，并验证私有文件绝不进入源码路径。案例研究提交不应暗中修改运行时策略或活跃评估语义。

## 发布就绪条件

公开项目版本从 v0.1.0 开始采用语义化版本控制。`0.x` 版本可以使用，但仍在演进。带注释的 Git 标签是不可变的发布身份标识。分发清单版本必须与 Git 发布标签一致，但不含开头的 `v`；当前 Claude Plugin 清单版本为 0.2.1，与 v0.2.1 一致。每次 Plugin 变更都必须递增清单版本，因为 Claude Code 将其作为更新键。基准测试修订标签与项目发布版本保持独立。

在面向公众的发布提交之前：

- 运行等同 CI 的验证；
- 对照起始树身份标识验证 `skills/`、活跃评估和已冻结输入；
- 检查完整差异和仓库状态；
- 对照 Codex 与 Claude Code 当前官方文档确认安装指南；
- 在缺乏明确策略与证据时，避免稳定性、采用率、精确率或生产环境方面的声明；
- 保持所有分发元数据与预期的 Git 发布标签一致。

不要根据基准测试标签推断产品版本，也不要移动已发布的版本标签。

## 分发兼容性说明

规范的 [`skills/deslop/`](../skills/deslop/) 运行时保持标准兼容，并由各宿主原样共享。Codex 将其作为 `.agents/skills` 下的独立 Skill 发现；Claude Code 可以在 `.claude/skills` 下发现同一目录，也可以通过仓库的 Claude Plugin 发现它。OpenAI 专用的 [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml) 控制 Codex UI 元数据与仅限明确调用的行为，Claude Code 会忽略该文件。

Claude Code 打包配置通过 [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) 和 [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) 提供。仓库根目录就是 Plugin 根目录，因此 Claude 使用默认的 `skills/<name>/SKILL.md` 扫描方式，并公开规范的带命名空间命令 `/deslop:deslop`。清单声明 0.2.1，对应的 `v0.2.1` 标签固定了该版本。v0.2.1 新增分发元数据和双语项目文档，而运行时 Skill 载荷与 v0.2.0 逐字节一致。未来每次 Plugin 变更都必须递增清单值，以供更新检测。

Codex Plugin 打包仍是一个独立且尚未解决的宿主问题。经测试的宿主版本为 Codex CLI 0.149.1。Plugin Creator 验证接受了一个临时的仅含 Skills 的清单，其中包含 `skills: "./skills/"`；本地 marketplace 的发现、安装与缓存创建也均成功。缓存中包含 `skills/deslop/SKILL.md`，但移除环境中的独立 Skill 后，新启动的 app-server 执行 `skills/list(forceReload=true)` 时并未返回已注册的 `deslop` Skill。因此，当前阻碍在于 Codex Plugin 到宿主的 Skill 注册，而非规范运行时布局或独立 Skill 的有效性。Claude 专用的 `.claude-plugin/` 元数据不会改变这一结果，也不能替代受支持的 Codex 独立安装路径。
