# `dev-v3-evidence-edges` 草案

**简体中文** · [English](README.md)

这套后续评测把 2026-09-02 一次真实项目复核中总结出的规律匿名化，整理为成对的证据边界案例。它不会修改或重新计算已经冻结的 `dev-v2-focused-rc5` fixture、grader 或结果。

同一份复核也用于更新本次 Skill 规则，因此这是一套答案已暴露的开发回归集，不是证明 Skill 效果的独立留出证据。任何关于模型效果的结论都必须另用未受污染的 corpus。

## 收录内容

原始复核共整理出 19 组正反观察，统一记录在 [`evidence-bank.json`](evidence-bank.json) 中。这里的**正例**表示证据支持删除、合并或改成直接报错；**反例**表示附近看似相同的结构拥有独立依据，必须保留。

本草案先把其中九条观察合并为七组可执行案例：

| 案例对 | 类别 | 正例目标 | 反例边界 |
| --- | --- | --- | --- |
| `r01` | 生产可达性 | 删除只能由测试注入标志到达的分支 | 保留由当前生产配置选择的真实变体 |
| `r02` | 路径闭合 | 退休过时 package fixture 及其私有路径 | 保留一个从当前 producer 到 consumer 的 hermetic 集成根 |
| `h01` | 测试 hermeticity | 删除依赖一次性运行产物、平时只能 skip 的测试 | 保留仓库受管的协议 fixture |
| `h02` | 测试 hermeticity | 把 builder 测试的输出从 tracked 文件改到临时目录 | 保留只读 tracked source、写临时输出的测试 |
| `v03` | 权威 artifact | 对已声明的权威 artifact 执行强制存在与校验 | 保留协议明确允许缺失的可选 enrichment |
| `s01` | Schema 契约 | 让所有当前公开 reader 都拒绝旧 schema | 保留明确用于旧版本迁移的 reader |
| `s02` | Schema 契约 | 删除关键身份字段上的历史默认值 | 保留展示字段上有文档依据的可选默认值 |

仍有五条观察留在候选层：snapshot 范围、伪造成功的 dry-run、registry/CLI owner 闭环、fake-only 依赖 skip，以及失真的当前文档。证据库还标注了另外五条已经由 `dev-v2-focused` 覆盖的规律，并单独归纳了清理时必须保留的安全、持久化/协议、硬件/数值失败域。

## 动作与检查顺序

每个 `a` 案例要求执行 `simplify` 或 `repair`，附近的 `b` 案例负责保护边界。评分把四项判断分开：

1. **当前行为：** 合法的公开行为仍然可用。
2. **剩余测试：** 至少保留一项可发现且能够通过的测试。
3. **目标状态：** 无依据的结构已经删除，或 fail-open 契约已经修正。
4. **新增限制：** 不得新增文件、测试、依赖或抽象层；只有修复所需的少量 Python 行数增长可以接受。

每个正例都有 `golden_after` 校准；每个反例都有 `destructive_mutant`。在可行时，破坏性变体仍让普通测试保持绿色，只由隐藏边界检查发现问题。草案还包含其他有效实现和故意清理不彻底的状态，用来检查评分是否依赖某个固定补丁。

## 校验草案

先运行不依赖第三方包的校验器：

```bash
python3 scripts/validate_evidence_edges_corpus.py
```

安装固定版本的评测框架后，再校验 manifest：

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v3-evidence-edges/evals.json
```

目前不要用这份草案比较模型。应先冻结修订版本，复核隐藏契约是否泄漏答案或绑定某个补丁形状，再重新采集 baseline。本评测的结果也不能与 `dev-v2-focused` 的小案例或小型仓库结果混算。
