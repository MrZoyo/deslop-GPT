# `deslop` `dev-v1` 全量 Codex A/B pilot

状态：内部开发诊断，不是公开性能声明。

## 复现信息

- 全量运行提交：`a865d51405b167e2e54513ea704b7e0f060be197`
- 运行窗口：`2026-08-24T20:25:16Z`–`2026-08-24T21:28:05Z`（上海时间为 8 月 25 日）
- Corpus：development `dev-v1`，20 个语义 case + 1 个 audit control
- Harness：`agent-skill-eval==0.7.0`
- Codex CLI：`0.149.0`
- 模型：`gpt-5.6-sol`
- Reasoning：`medium`
- 每个 configuration：1 run；42 次模型调用；`concurrency=1`
- Sandbox：`workspace-write`
- Network：harness 未显式固定或记录
- Approval / 其他本地配置：除模型和 reasoning 外沿用本机 profile
- Cost telemetry：不可用；没有把未知成本写成 `$0`

运行前临时移开了用户级 `~/.agents/skills/deslop`，运行结束后恢复。with-Skill 每次都验证了 canonical `.agents/skills/deslop` 和内容 hash。

本次比较的是：

```text
baseline = 同一个强 evidence-backed cleanup prompt
           + 没有 Skill

with Skill = 同一个 prompt + 显式 $deslop
```

因此结果衡量的是 Skill 相对强任务提示的增量价值，不是相对普通或无提示 Codex 的提升。

Runtime Skill 在本次运行的 payload 为 7 个文件、34,126 bytes、4,352 words，content hash：
`a57136df515f13ab9240a73089acc537064e4f34646aa912eb51e76f8c4d2706`。

任务顺序由 wrapper 做 deterministic counterbalancing：audit 和奇偶 case/run 交替 `Skill → baseline` 与 `baseline → Skill`。实际 42 项启动顺序保存在机器结果中。

## 结果

| 指标 | Without Skill | With Skill | 差值（with − without） |
| --- | ---: | ---: | ---: |
| Behavior Preservation（10 个 preserve case） | 10/10 = 1.00 | 7/10 = 0.70 | −0.30 |
| Simplification Case Recall（10 个 simplify case） | 6/10 = 0.60 | 8/10 = 0.80 | +0.20 |
| 语义 full-case pass（20 个语义 case） | 16/20 = 0.80 | 15/20 = 0.75 | −0.05 |
| 平均 wall time | 75.287 s | 103.253 s | +27.965 s |
| 平均 total tokens | 102,115 | 165,037 | +62,923 |
| 平均 non-cached input | 16,741 | 26,900 | +10,159 |

配对四象限如下：

| 子集 | Both pass | Skill improves | Skill regresses | Both fail |
| --- | ---: | ---: | ---: | ---: |
| 全部 21 cases（含 audit） | 11 | 4 | 5 | 1 |
| simplify | 4 | 4 | 2 | 0 |
| preserve | 7 | 0 | 3 | 0 |
| audit | 0 | 0 | 0 | 1* |

`*` 全量运行的 audit 失败不是业务文件变更，而是当时 wrapper 的 side-effect 比较把 Codex 生成的 `__pycache__/` 视为 worktree mutation。这个 harness bug 已在 `67d168c88274cbe8484448314f30c2cf75c7996b` 修复；随后独立 audit recheck 得到：

```text
with Skill:    2/2 assertions pass
without Skill: 2/2 assertions pass
```

所以全量 JSON 中 audit 的原始 0/1 不应作为最终 authorization 指标；请同时查看 [`dev-v1-audit-recheck-20260825.json`](dev-v1-audit-recheck-20260825.json)。这次没有用后验结果改写全量运行的原始记录。

## 失败分布

### Skill-only improvements

- `c01a`：删除未使用 parser/digest helper 的完整目标状态。
- `c02a`：删除冗余 aggregate assertion，同时保留更强的 per-result contract。
- `c05a`：去除 timestamp-derived rotation 推断。
- `c10a`：支持多个独立嵌入 calibration；baseline 反而触发了测试膨胀的 negative-change budget。

### Skill-only regressions

- `c03a`：Skill 删除了唯一测试，remaining-test gate 报告 `NO TESTS RAN`。
- `c07a`：adapter 仍复制 sensitive-key policy，simplify 目标未完整收敛。
- `c07b`：preserve case 的 sanitizer 失去 idempotence。
- `c09b`：preserve case 接受了被篡改的 frozen ledger。
- `c10b`：preserve case 出现 `TypeError: cannot unpack non-iterable PosixPath object`。

baseline-only failures 为 `c01a`、`c02a`、`c05a` 的语义 gate，以及 `c10a` 的 negative-change budget；两种配置均通过其余 preserve case。完整 gate evidence、structural delta、timing 和 trajectory 计数都在机器结果中，未发布模型 transcript 或 reasoning。

## 解释与下一步

这次 pilot 不支持“deslop 提升了 X%”的说法。它给出了一个清晰但混合的开发信号：Skill 在 simplify recall 上有 +20 个百分点，但 Behavior Preservation 从 100% 降到 70%，语义总体从 80% 降到 75%。在这个项目的 KPI 顺序下，preserve 回归优先于删除率提升。

因此本轮不直接修改 `SKILL.md`。下一步应先针对 `c03a/c07b/c09b/c10b` 做失败证据审查，确认是共同的 apply/uncertainty 解释问题、模型随机性，还是 grader/fixture 绑定问题；在没有 holdout 之前也不发布效果声明。当前 20 个 case 已继续作为 development corpus，不能作为 Skill 调优后的泛化证明。

机器可读、无 transcript 的全量记录见 [`dev-v1-full-pilot-20260825.json`](dev-v1-full-pilot-20260825.json)。原始 harness artifacts 保留在本地忽略目录 `eval-workspace/deslop-dev-v1-full/`，没有提交到仓库。
