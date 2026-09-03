# rc5 case follow-up on Claude Code — Haiku 4.5, 2026-09-03

Status: internal development diagnostic. Machine-readable record: [`rc5-claude-haiku-follow-up-20260903.json`](rc5-claude-haiku-follow-up-20260903.json).

This repeats the five cases of the [rc5 targeted follow-up](rc5-targeted-follow-up-20260826.json) — `t01b`, `t02b`, `t03b`, `f01a`, `f02a` — against the exact v0.3.1 runtime payload (`39146983…`), through the Claude Code CLI rather than Codex. It is **not** comparable with the rc5 Codex numbers: different host, different model, and no without-Skill baseline. Read it as a preservation check on one more host, not as a model comparison.

| Setting | Value |
| --- | --- |
| Harness | `agent-skill-eval==0.7.0`, `.claude/skills/deslop` discovery, `/deslop` invocation |
| Agent CLI | Claude Code 2.1.259 |
| Model | `claude-haiku-4-5-20251001` |
| Runs | 3 per case, 15 model calls, concurrency 1, no retries |
| Baseline | None |
| Hidden gates | `evals/dev-v2-focused/grade_focused.py` as the post-grade hook |

## Results

| Case | Expected | Full-pass runs | Failing gate |
| --- | --- | ---: | --- |
| `t01b` | preserve | 3/3 | — |
| `t02b` | preserve | 1/3 | hidden behavior, twice |
| `t03b` | preserve | 3/3 | — |
| `f01a` | simplify | 2/3 | reduction target, once |
| `f02a` | simplify | 3/3 | — |

Twelve of fifteen runs passed every gate. Every run passed its side-effect contract and left a passing test suite, and no run breached the negative-change budget.

## The `t02b` regression

In runs 1 and 3 the model deleted the `legacy_header` branch of `parse_header` together with the test that covered it, reported HIGH confidence, and described the pair as mutual-support slop with "no independent external evidence for legacy compatibility". The hidden gate then failed on `parse_header({"legacy_header": "v1"})`.

This is the exact failure `t02b` exists to catch, and the exact reasoning `SKILL.md` argues against: a test may be the clearest executable specification of a supported compatibility behavior, so deleting the test is not evidence for deleting the behavior. The v0.3.1 payload states that rule; on this model it did not hold two runs out of three.

The earlier Codex subagent smoke recorded `t02b` passing once. One run could not have surfaced this; three runs on a smaller model did.

## The `f01a` miss

One `f01a` run preserved behavior but left fallback control flow in place, so it failed the reduction target rather than the behavior gate. That is the conservative direction of failure.

## What this does not establish

Three runs per case cannot separate a payload weakness from model variance, and five known development cases are not a held-out corpus. Without a baseline this says nothing about whether the Skill helps relative to the same prompt without it. The result must not be combined with the rc5 Codex figures or with any mini-repository score.
