# `dev-v2-focused`

**简体中文** · [English](README.md)

这是一个面向编码 agent 反复实施和修正周期所累积复杂性的新开发语料库。它有意与历史 `dev-v1` 分离；不要为了最大化任一语料库而调优 Skill，也不要合并两者分数。

## 范围与配比

微案例层包含 8 对删除/保留案例：

| 类别 | 删除案例 | 占比 | 重点 |
| --- | ---: | ---: | --- |
| 测试膨胀 | 4 | 50% | 重复和连续回归测试、私有辅助函数测试、仅包装器测试 |
| 验证表演 | 2 | 25% | 自生成校验和/回执集群与独立工件验证的对比 |
| 防御/回退膨胀 | 2 | 25% | 宽泛捕获并回退、过时恢复与有文档的兼容/清理契约的对比 |

每个 `a` 删除案例都有相同配对前缀的相邻 `b` 保留反例。标签和根因保存在 [`adjudication.json`](adjudication.json)，而不放入复制给 agent 的文件。

案例层有意不做通用死代码或抽象基准。只有属于测试膨胀、验证表演或防御/回退累积的构造才在范围内。

## 案例校准

每个删除案例有一个 `golden_after` 覆盖，每个保留案例有一个 `destructive_mutant` 覆盖。每一类别至少维护两个 `alternate_valid` 状态。隐藏行为门槛从不要求测试数量、测试名、辅助函数形态或历史补丁。行为与剩余测试通过后才单独检查缩减目标：测试膨胀微案例最多保留一个充分测试；本地验证表面必须归零；捕获/回退微案例必须移除回退控制流，而非仅把捕获改写为分支。每类有一个 `insufficient_cleanup` 状态，在保留行为并移除部分表面的同时故意无法达到阈值。

每个微案例还有负向变更硬门槛：拒绝新增 Python 文件或依赖、新测试、语法错误、新抽象或类别目标机制，以及超过四行新增非空 Python 代码。四行额度用于保留现有表驱动备选有效案例，并非通用增长预算。

## 端到端累积冗余层

三个微型仓库模拟经历多轮 agent 修正后的代码，而不是孤立的 20 行代码异味：

1. [`mini-repos/test-bloat`](mini-repos/test-bloat)：小型报告包，包含重叠回归测试、私有辅助函数测试，以及一套有意义的公开行为测试。
2. [`mini-repos/verification-bloat`](mini-repos/verification-bloat)：报告写入器周围环绕自生成校验和、信封、回执、验证器及仅验证器测试机制，同时必须保留独立的持久化回读契约。
3. [`mini-repos/fallback-bloat`](mini-repos/fallback-bloat)：当前解析器外包裹宽泛捕获回退层、重复验证和过时兼容测试，同时必须保留有文档的旧协议与原子清理契约。

[`grade_focused.py`](grade_focused.py) 中的隐藏微型仓库评分器先评估有外部意义的行为，再评估缩减。每个仓库都有已知良好的 [`mini-repo-calibration/`](mini-repo-calibration/) `golden_after` 状态，必须通过行为、剩余测试、有意义缩减和负向变更门槛。`test-bloat` 的测试数量、测试 LOC 和测试夹具调用次数均须至少减半；`verification-bloat` 的本地验证器函数必须清零、校验和提及至少减半，且只允许保留独立回读哈希操作；`fallback-bloat` 中捕获后返回的解析器回退必须消失，而原子清理捕获须保留。

只有 agent 生成副本通过隐藏行为门槛后，才能将其与未修改的微型仓库比较：

```bash
python3 evals/dev-v2-focused/grade_focused.py compare \
  test_bloat \
  evals/dev-v2-focused/mini-repos/test-bloat \
  /path/to/cleaned/test-bloat
```

比较结果会输出前后生产代码与测试 LOC、测试数量/运行时间、测试夹具调用、结构差异、校验和/验证/回退提及、类别缩减判断和负向变更判断。失败的清理后状态无资格计入缩减评分。

逐案例复核记录在 [`review.md`](review.zh-CN.md)。工作修订版是 `dev-v2-focused-rc5` 候选；已发布的 rc3 微案例和 rc4 微型仓库试运行仍作为不变的历史证据。

三个仓库可通过 [`mini-evals.json`](mini-evals.json) 交给模型运行。后评分钩子把每个微型仓库 ID 解析到其未修改测试夹具，并调用 `compare_mini_repositories()`；不会使用第二套编排框架。

## 运行轻量验证器

聚焦语料库有自己的无依赖验证器，避免把历史 `dev-v1` 验证器扩展成更大的通用框架：

```bash
python3 scripts/validate_focused_corpus.py
```

它检查配对对称性、类别配比、中性测试夹具边界、基线测试、清理不足极性、所有负向变更规则、两个模型清单和三个微型仓库门槛，但不声称模型已解决该语料库。

安装固定版本的执行框架依赖后，验证两个清单：

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/dev-v2-focused/mini-evals.json
```

## 解读

本层旨在回答：

> deslop 能否在不破坏有意义行为的前提下，大幅减少累积的测试与防御机制？

这不是代码行删除竞赛。`Simplification Case Recall` 衡量案例是否达到经裁定的更简状态；缩减幅度单独报告，且仅在隐藏行为门槛通过后报告。

[`evals.json`](evals.json) 的结果是 **16 案例聚焦微案例 A/B 诊断**。[`mini-evals.json`](mini-evals.json) 的结果是独立的 **三个仓库端到端 A/B**。后者才是整个累积冗余清理的证据；两者分数不得合并或错误标注。

本次变更有意不加入插件包、新依赖、第二套 A/B 编排框架、留出语料库或模型结果自动发布。这些工作应等聚焦测试夹具和隐藏契约通过复核后再进行。
