# 当前评测规则

**简体中文** · [English](README.md)

当前使用的开发基准是 [`dev-v2-focused`](dev-v2-focused/README.zh-CN.md)。它专门检查编程 Agent 在多轮实现和修正中积累的复杂代码，不是通用代码清理基准：

- 测试膨胀：4 对案例（50%）；
- 形式大于实效的验证：2 对案例（25%）；
- 过度防御与回退逻辑：2 对案例（25%）。

16 个小案例中，每个“应删除”案例都有一个编号前缀相同的“应保留”对照案例；同时提供已知正确的结果、会破坏行为的错误改法，以及其他有效方案，用来校准评分。另有三个小型仓库，在整库规模上模拟逐步累积的冗余测试、形式大于实效的验证和回退逻辑。

`dev-v2-focused-rc5` 已经冻结。另建的 [`dev-v3-evidence-edges`](dev-v3-evidence-edges/README.zh-CN.md) 草案收录了 19 条匿名化现场观察，并先把其中 7 组做成可执行案例，覆盖生产可达性、测试 hermeticity、权威 artifact 和 schema 契约。CI 会校验它的内部一致性，但它目前还不能用于模型对比，结果也不能与 `dev-v2-focused` 混算。

[`runtime-controls`](runtime-controls/README.zh-CN.md) 单独检查授权边界和其他宿主运行时承诺。这些控制案例既不是清理质量案例，也不计入任何语料分数。

绑定具体版本的小型前向测试保存在 [`release-smoke`](release-smoke/) 下。它们始终属于已暴露的开发诊断，不能替代冻结的 A/B 或独立留出集。

## 真实项目证据

经人工复核的真实项目案例作为历史证据，单独保存在 `real-world/` 下。它们不属于当前的定量基准评测，也不能根据单个仓库的结果反过来调优 Skill。参见 [`cluster-gpu-monitor` 案例](real-world/cluster-gpu-monitor/README.zh-CN.md)。

## 硬性检查顺序

专项评分依次执行四项硬性检查：

1. **行为检查：** 必须保留当前协议和仍受支持的旧协议行为、对外输出、持久化数据损坏检测、安全与来源真实性边界，以及原子操作失败后的清理责任。评分不能限定测试函数数量、测试名称、辅助函数结构或某个历史补丁。
2. **现有测试检查：** 清理后至少还要有一项能被测试框架识别的测试，并且整个测试套件通过。
3. **精简目标：** 清理后的代码必须达到人工审核为该类别设定的阈值；只删一个 `token` 或一个重复项不算真正完成清理。
4. **新增内容限制：** 清理不能新增 Python 文件、测试、依赖、包装层或抽象层、目标类别中的新机制或语法错误；新增的非空 Python 代码也不能超过四行。

对于小型仓库，只有现有测试和隐藏行为检查都通过，精简指标才会计入评分。清理结果只要有一项失败，就不会获得部分精简分。

`Simplification Case Recall`（简化案例召回率）按案例判断语义简化是否正确，不是删除代码行数的百分比。具体精简幅度单独报告，而且只统计通过上述检查的结果。

## 运行模型前先验证

```bash
python3 scripts/validate_focused_corpus.py
python3 scripts/validate_evidence_edges_corpus.py

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

专项校验程序会检查：

- 16 个成对案例的 ID，以及 4/2/2 的目标类别配比；
- 原始样例的测试结果和行为结果是否符合预期；
- `golden_after` 正确方案与 `destructive_mutant` 破坏性方案是否分别通过和失败；
- 三个类别中故意清理不彻底的方案能否被拒绝；
- 每个类别是否至少有两种其他有效方案；
- 每一种禁止新增内容的失败情况；
- 三个小型仓库的行为检查、精简目标和指标条件；
- 包含 16 个小案例的 manifest，以及包含 3 个小型仓库的 manifest。

`dev-v2-focused-rc5` 已经冻结。`dev-v3-evidence-edges-draft1` 仍在变化期间，不要对它运行 GPT A/B；应先完成复核并冻结版本，再收集可比结果。已经发布的 rc3 小案例试运行和 rc4 小型仓库试运行应继续作为两组独立的历史证据保存。

## 版本冻结后的模型运行方式

第一条命令运行 **包含 16 个专项小案例的 A/B 诊断**：

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skills/deslop \
  --evals evals/dev-v2-focused/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 1 \
  --concurrency 1 \
  --baseline \
  --post-grade-command "python3 evals/dev-v2-focused/grade_focused.py" \
  --workspace eval-workspace/deslop-dev-v2-focused
```

另一项独立的 **三仓库端到端 A/B 测试** 使用同一个适配脚本和评分后处理：

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skills/deslop \
  --evals evals/dev-v2-focused/mini-evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 1 \
  --concurrency 1 \
  --baseline \
  --post-grade-command "python3 evals/dev-v2-focused/grade_focused.py" \
  --workspace eval-workspace/deslop-dev-v2-focused-mini
```

小案例诊断无法衡量对完整小型仓库的清理能力。两组结果及其名称必须始终分开。

如果没有固定的评测版本、完整的模型与配置元数据、每个案例未经汇总的检查结果，以及独立留出的评测集，就不能发布这些命令产生的结果。

## 已退役的 `dev-v1`

覆盖范围较广、包含 20 个案例的 `dev-v1` 已不再用作当前调优基准。它的测试样例、旧评分程序、评测规则和历史诊断结果保存在 [`archive/dev-v1/`](archive/dev-v1/) 中，只用于回顾历史和参考较宽范围的安全回归。当前 CI 不会运行它。
