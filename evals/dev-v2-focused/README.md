# `dev-v2-focused`

[简体中文](README.zh-CN.md) · **English**

This is a new development corpus for accumulated complexity created by repeated coding-agent implementation and correction cycles. It is intentionally separate from historical `dev-v1`; do not tune the Skill to maximize either corpus and do not combine their scores.

## Scope and mix

The micro-case layer has 8 paired deletion/preservation cases:

| Category | Deletion cases | Share | Focus |
| --- | ---: | ---: | --- |
| Test bloat | 4 | 50% | duplicate and successive regression tests, private-helper tests, wrapper-only tests |
| Verification theater | 2 | 25% | self-generated checksum/receipt clusters versus independent artifact verification |
| Defensive/fallback bloat | 2 | 25% | broad catch-and-fallback and obsolete recovery versus documented compatibility/cleanup contracts |

Every `a` deletion case has a nearby `b` preservation counterexample with the same pair prefix. Labels and roots are kept in [`adjudication.json`](adjudication.json), not in the files copied to an agent.

The case layer is deliberately not a generic dead-code or abstraction benchmark. A construct is in scope only when it belongs to test bloat, verification theater, or defensive/fallback accumulation.

## Case calibration

Each deletion case receives a `golden_after` overlay and each preservation case a `destructive_mutant` overlay. At least two `alternate_valid` states are maintained in every category. The hidden behavior gate never requires a test count, test name, helper shape, or historical patch. Reduction targets are checked separately after behavior and remaining tests: test-bloat micro cases must reach at most one sufficient test, local verification surfaces must reach zero, and catch/fallback micro cases must remove fallback control flow rather than merely rewrite the catch as a branch. One `insufficient_cleanup` state per category preserves behavior and removes some surface while deliberately failing that threshold.

Every micro case also has a negative-change hard gate. It rejects new Python files or dependencies, added tests, syntax errors, new abstractions or category-target machinery, and more than four positive nonblank Python lines. The four-line allowance preserves the existing table-driven alternate-valid cases; it is not a general growth budget.

## End-to-end accumulated-slop layer

The three mini repositories model code after several agent correction cycles rather than isolated 20-line smells:

1. [`mini-repos/test-bloat`](mini-repos/test-bloat): a small reporting package with overlapping regression tests, private-helper tests, and one meaningful public behavior suite.
2. [`mini-repos/verification-bloat`](mini-repos/verification-bloat): a report writer surrounded by self-generated checksum, envelope, receipt, validator, and validator-only test machinery, plus an independent persisted readback contract that must remain.
3. [`mini-repos/fallback-bloat`](mini-repos/fallback-bloat): a current parser wrapped in broad catch-and-fallback layers, repeated validation, and obsolete compatibility tests, alongside a documented legacy protocol and atomic cleanup contract that must remain.

The hidden mini-repo grader in [`grade_focused.py`](grade_focused.py) evaluates externally meaningful behavior before reduction. Each repository has a known-good [`mini-repo-calibration/`](mini-repo-calibration/) `golden_after` state that must pass behavior, remaining-test, meaningful-reduction, and negative-change gates. Test count, test LOC, and fixture invocations must each fall by at least half in `test-bloat`; local verifier functions must clear, checksum mentions must fall by at least half, and only the independent readback hash operation may remain in `verification-bloat`; the catch-and-return parser fallback must disappear while the atomic cleanup catch remains in `fallback-bloat`.

Compare an untouched mini repository with an agent-produced copy only after the copy has passed its hidden behavior gate:

```bash
python3 evals/dev-v2-focused/grade_focused.py compare \
  test_bloat \
  evals/dev-v2-focused/mini-repos/test-bloat \
  /path/to/cleaned/test-bloat
```

The comparison emits before/after production and test LOC, test count/runtime, fixture invocations, structural deltas, checksum/verification/fallback mentions, a category reduction decision, and the negative-change decision. A failed after-state is ineligible for reduction scoring.

The case-by-case review is recorded in [`review.md`](review.md). Revision `dev-v2-focused-rc5` is frozen at its immutable benchmark tag; published rc3 micro and rc4 mini pilots remain unchanged historical evidence.

The three repositories are model-runnable through [`mini-evals.json`](mini-evals.json). The post-grade hook resolves each mini ID to its untouched fixture and calls `compare_mini_repositories()`; no second orchestration framework is used.

## Running the lightweight validator

The focused corpus has its own dependency-free validator so the historical `dev-v1` validator does not become a larger general framework:

```bash
python3 scripts/validate_focused_corpus.py
```

This checks pair symmetry, category mix, neutral fixture boundaries, baseline tests, insufficient-cleanup polarity, every negative-change rule, both model manifests, and the three mini-repository gates. It does not claim that a model has solved the corpus.

Validate both harness manifests after installing the pinned harness dependency:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/dev-v2-focused/mini-evals.json
```

## Interpretation

The purpose of this layer is to answer:

> Can deslop substantially reduce accumulated test and defensive machinery without breaking meaningful behavior?

It is not a line-deletion contest. `Simplification Case Recall` measures whether a case reaches its adjudicated simpler state; reduction magnitude is reported separately and only after hidden behavior gates pass.

Results from [`evals.json`](evals.json) are a **16-case focused micro-case A/B diagnostic**. Results from [`mini-evals.json`](mini-evals.json) are the separate **three-repository end-to-end A/B**. The latter is the evidence about whole accumulated-slop cleanup; the two scores must not be combined or mislabeled.

This change deliberately does not add a plugin package, a new dependency, a second A/B orchestration framework, a holdout corpus, or automatic model-result publishing. Those belong after the focused fixtures and hidden contracts survive review.
