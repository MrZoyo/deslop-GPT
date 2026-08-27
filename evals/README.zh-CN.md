# 当前评估协议

**简体中文** · [English](README.md)

当前开发基准为 [`dev-v2-focused`](dev-v2-focused/README.zh-CN.md)。它针对反复编码 agent 周期造成的累积复杂性，而非通用清理：

- 测试套件膨胀：4 对案例（50%）；
- 验证表演：2 对案例（25%）；
- 防御/回退膨胀：2 对案例（25%）。

16 个微案例均有相同前缀的保留反例、黄金/突变极性校准和备选有效校准。三个微型仓库在仓库尺度模拟累积的测试、验证与回退冗余。

## 真实世界证据

人工裁定的现场试验作为历史证据单独保存在 `real-world/` 下。它们目前不属于当前定量基准，也不得依据单一仓库用于调优 Skill。参见 [`cluster-gpu-monitor` 案例研究](real-world/cluster-gpu-monitor/README.zh-CN.md)。

## 硬门槛顺序

聚焦评分分为四道门槛：

1. **行为门槛：** 当前/旧协议行为、公开输出、持久化损坏检测、安全/溯源边界和原子清理。不得规定测试函数数、测试名、辅助函数形态或历史补丁。
2. **剩余测试门槛：** 至少保留一个可发现测试，且套件通过。
3. **缩减目标：** 清理后状态在裁定中达到类别阈值；只删除一个 token 或一个重复项并不充分。
4. **负向变更门槛：** 清理不得新增 Python 文件、测试、依赖、包装器/抽象、类别机制或语法错误，新增的非空 Python 正行数也不得超过四行。

对于微型仓库，只有剩余测试套件和隐藏行为门槛均通过，缩减指标才有效。失败的清理后状态不会获得部分缩减分。

`Simplification Case Recall` 是案例级语义召回率，不是删除行数百分比。缩减幅度单独报告，且只针对合格状态。

## 运行模型前先验证

```bash
python3 scripts/validate_focused_corpus.py

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/mini-evals.json
```

聚焦验证器检查：

- 16 个配对 ID 及 4/2/2 目标配比；
- 基线测试与行为极性；
- 黄金后状态与破坏性突变体的极性；
- 三个类别中的清理不足拒绝；
- 每个类别至少两个备选有效状态；
- 每种负向变更失败模式；
- 三个微型仓库的行为、缩减与指标门槛；
- 16 案例微型清单与 3 案例微型仓库清单。

修改该语料库期间不要运行 GPT A/B。当前工作修订版是 `dev-v2-focused-rc5` 候选；收集新的可比结果前应先冻结。已发布的 rc3 微案例和 rc4 微型仓库试运行应作为彼此分离的历史证据保留。

## 冻结后的模型运行形式

第一条命令执行 **16 案例聚焦微案例 A/B 诊断**：

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

独立的 **三个仓库端到端 A/B** 使用同一包装器和钩子：

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

微案例诊断不衡量完整微型仓库清理。应将两组结果及其名称分开。

若没有冻结修订版、模型/配置元数据、逐案例原始门槛以及独立留出语料库，这些命令产生的结果均不可发布。

## 已退役的 `dev-v1`

宽泛的 20 案例 `dev-v1` 套件已不再是当前调优基准。其测试夹具、旧评分器、协议和历史诊断保存在 [`archive/dev-v1/`](archive/dev-v1/) 下，用于历史记录和宽泛安全回归参考。当前 CI 不运行它。
