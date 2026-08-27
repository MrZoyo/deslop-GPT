# deslop 文档

**简体中文** · [English](README.md)

选择与目标最匹配的最短路径：

| 目标 | 从这里开始 |
| --- | --- |
| 安全安装并使用 `deslop` | [入门指南](getting-started.zh-CN.md) |
| 了解为何接受或保留某项清理 | [设计](design.zh-CN.md) |
| 查看聚焦开发证据 | [评估](evaluation.zh-CN.md) |
| 查看真实案例研究方法 | [现场试验](field-trials.zh-CN.md) |
| 验证、贡献或发布仓库 | [开发](development.zh-CN.md) |

顶层 [README](../README.zh-CN.md) 是项目公开概览。详细基准机制以 [`evals/`](../evals/README.zh-CN.md) 下文档为准；自包含运行时 [`SKILL.md`](../skills/deslop/SKILL.md) 是 agent 行为的权威来源。

## 文档边界

- `docs/` 面向用户和贡献者解释项目。
- `.claude-plugin/` 为 Claude Code 打包共享运行时并发布 marketplace 条目。
- `skills/deslop/` 是自包含的运行时载荷。
- `evals/dev-v2-focused/` 是当前开发评估。
- `evals/real-world/` 保存人工裁定的历史证据。

此处仅修改说明性文字，不会改变运行时策略或评估语义。

项目维护文档均提供英文与简体中文版本。运行时 Skill 指令、冻结的评估输入、历史结果和参考证据保留其规范语言，因为翻译这些内容会改变可执行策略或冻结证据的身份标识。
