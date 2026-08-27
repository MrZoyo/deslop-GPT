# deslop 文档

**简体中文** · [English](README.md)

按你的目的选择最直接的文档：

| 目标 | 从这里开始 |
| --- | --- |
| 安装并安全使用 `deslop` | [入门指南](getting-started.zh-CN.md) |
| 了解一项清理为什么应当执行或保留 | [设计](design.zh-CN.md) |
| 查看专项开发评测及其证据 | [评测](evaluation.zh-CN.md) |
| 了解真实项目案例的记录方法 | [真实项目试用](field-trials.zh-CN.md) |
| 验证仓库、参与贡献或准备发布 | [开发](development.zh-CN.md) |

顶层 [README](../README.zh-CN.md) 是项目概览。基准评测的具体规则以 [`evals/`](../evals/README.zh-CN.md) 中的文档为准；Agent 实际执行的规则则以独立完整的 [`SKILL.md`](../skills/deslop/SKILL.md) 为准。

## 文档边界

- `docs/`：面向用户和贡献者的项目说明。
- `.claude-plugin/`：将共用的 Skill 打包为 Claude Code Plugin，并提供插件市场配置。
- `skills/deslop/`：可以独立使用的完整 Skill 运行时文件。
- `evals/dev-v2-focused/`：当前使用的开发评测。
- `evals/real-world/`：经人工复核并冻结留档的真实项目证据。

这里只是项目说明。修改这里的文字，不会改变 Skill 的执行规则或评测标准。

持续维护的项目文档同时提供英文和简体中文版本。Skill 运行指令、已冻结的评测输入、历史结果与参考证据则保留原始语言，因为翻译它们会改变实际执行的规则，或破坏冻结材料与原版本的一一对应关系。
