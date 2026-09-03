# Evaluation

[简体中文](evaluation.zh-CN.md) · **English**

The evaluation material tests whether `deslop` can simplify accumulated machinery without erasing meaningful behavior. It is development evidence, not a claim of general model superiority.

[`evals/README.md`](../evals/README.md) is the canonical protocol. The active corpus documentation lives in [`evals/dev-v2-focused/`](../evals/dev-v2-focused/README.md); this page provides navigation and interpretation rather than a competing copy of every command and threshold.

## Active focused corpus

`dev-v2-focused` has two distinct layers:

| Layer | Shape | Purpose |
| --- | --- | --- |
| Focused micro cases | 8 deletion/preservation pairs, 16 cases total | Diagnose semantic decisions in test, verification, and fallback clusters |
| End-to-end miniature repositories | 3 accumulated-slop repositories | Measure whole-repository behavior preservation and meaningful reduction |

Every deletion target has a nearby preservation counterexample. Calibration states include known-good cleanups, destructive mutants, alternate valid solutions, and deliberately insufficient cleanups. This tests both over-preservation and over-deletion without requiring an agent to reproduce one historical patch.

Micro-case and miniature-repository results are separate. They must not be combined into one score or described as measuring the same layer.

## Follow-up evidence-edge draft

[`dev-v3-evidence-edges`](../evals/dev-v3-evidence-edges/README.md) is a separate draft derived from 19 anonymized field observations. Seven paired fixtures currently exercise production reachability, current-path integration roots, managed test inputs and outputs, authoritative artifact presence, complete schema-reader enforcement, and required-field defaults.

The draft introduces `repair` cases where cleanup exposes a fail-open current contract, alongside ordinary `simplify` and `preserve` decisions. Because the same field review informed the Skill update, this is exposed development regression evidence rather than a holdout. It has offline polarity calibration but no frozen model baseline, so it is not part of the active quantitative benchmark and must not be combined with `dev-v2-focused` results.

## Runtime controls and release smokes

[`runtime-controls`](../evals/runtime-controls/README.md) checks default read-only behavior separately from cleanup quality. Three cases reach one shared input through an explicit audit, a cleanup-shaped request with no explicit invocation, and a question that asks for no cleanup at all. None authorizes a worktree change, and none contributes a simplification or preservation score. Because the harness reports no automatic Skill-usage signal, whether the Skill was selected is read from the transcript rather than graded.

[`release-smoke`](../evals/release-smoke/) binds small forward tests to exact Skill content hashes. These runs can expose packaging, authorization, or gross behavioral regressions, but their known fixtures, single runs, and missing baselines make them development diagnostics rather than model-effect evidence.

## Decision order

Reduction is eligible only after safety and behavior gates pass:

1. **Behavior gate:** preserve public behavior, protocols, supported compatibility, persistence, security, and cleanup contracts.
2. **Remaining-test gate:** keep a discovered, passing test suite.
3. **Reduction target:** remove enough category-specific machinery to constitute meaningful simplification.
4. **Negative-change gate:** reject new dependencies, tests, wrappers, abstractions, syntax failures, and other cleanup-induced growth.

`Simplification Case Recall` is case-level semantic recall, not a percentage of lines deleted. Reduction magnitude is reported separately and only for eligible states.

## Run discipline

Comparable model runs require:

- a frozen Skill and corpus revision;
- a pinned model, reasoning effort, Codex version, and harness version;
- repeated runs with recorded run count, order, token cost, and wall time;
- raw per-case behavior and reduction gates;
- an uncontaminated without-Skill baseline;
- separate reporting for micro and mini-repository layers;
- held-out evidence before any broad public model-effect claim.

The wrapper in [`scripts/run_agent_skill_eval.py`](../scripts/run_agent_skill_eval.py) handles the pinned `agent-skill-eval 0.7.0` compatibility boundary, temporary Skill discovery, baseline isolation checks, and the required post-grade hook. Use the exact commands in the canonical [`evals/README.md`](../evals/README.md).

## Interpretation limits

- Passing corpus validation proves corpus consistency, not model performance.
- A pilot result is a diagnostic tied to its exact frozen revision and run configuration.
- Fixture count, passing pre-cleanup tests, assertion mean, or raw line deletion does not prove Skill effectiveness.
- Adding or changing a safety gate can change an aggregate assertion rate without changing model behavior.
- The repository publishes no project-level performance score.
- A real-world field trial is not interchangeable with a controlled benchmark run.

## Historical material

The broad `dev-v1` suite is retired under [`evals/archive/dev-v1/`](../evals/archive/dev-v1/README.md). It remains available for historical diagnostics and broad safety-regression reference, but active CI does not treat it as the development benchmark.

Published pilot artifacts remain under their respective evaluation directories. They are development history, not cross-version performance claims.

## Tooling context

The evaluation workflow was informed by [agent-skill-eval](https://github.com/tardigrde/agent-skill-eval) and [SkillBenchmark](https://github.com/TiesPetersen/SkillBenchmark). Their inclusion does not imply endorsement or make results comparable across different corpus, Skill, model, or harness revisions.
