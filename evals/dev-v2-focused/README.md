# `dev-v2-focused`

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

Each deletion case is expected to receive a `golden_after` overlay and each preservation case a `destructive_mutant` overlay before model scoring is published. The hidden gate must establish behavior first; reduction metrics are secondary. A valid golden may remove production and tests together when the tests only protected the removed slop.

## End-to-end accumulated-slop layer

The three mini repositories model code after several agent correction cycles rather than isolated 20-line smells:

1. [`mini-repos/test-bloat`](mini-repos/test-bloat): a small reporting package with overlapping regression tests, private-helper tests, and one meaningful public behavior suite.
2. [`mini-repos/verification-bloat`](mini-repos/verification-bloat): a report writer surrounded by self-generated checksum, envelope, receipt, validator, and validator-only test machinery, plus an independent persisted readback contract that must remain.
3. [`mini-repos/fallback-bloat`](mini-repos/fallback-bloat): a current parser wrapped in broad catch-and-fallback layers, repeated validation, and obsolete compatibility tests, alongside a documented legacy protocol and atomic cleanup contract that must remain.

The hidden mini-repo grader in [`grade_focused.py`](grade_focused.py) evaluates externally meaningful behavior before reduction. It records production/test LOC, test count, test runtime when stable, expensive fixture invocations, functions/classes/branches, try/except count, checksum/verification machinery, new tests, and new wrappers/fallbacks. Metrics are not a success signal when a behavior gate fails.

Compare an untouched mini repository with an agent-produced copy only after the copy has passed its hidden behavior gate:

```bash
python3 evals/dev-v2-focused/grade_focused.py compare \
  test_bloat \
  evals/dev-v2-focused/mini-repos/test-bloat \
  /path/to/cleaned/test-bloat
```

The comparison emits before/after production and test LOC, test count/runtime, fixture invocations, structural deltas, checksum/verification/fallback mentions, and explicit counts of newly added tests, wrappers, abstractions, and fallbacks.

## Running the lightweight validator

The focused corpus has its own dependency-free validator so the historical `dev-v1` validator does not become a larger general framework:

```bash
python3 scripts/validate_focused_corpus.py
```

This checks pair symmetry, category mix, neutral fixture boundaries, baseline tests, calibration polarity, and the three mini-repository behavior gates. It does not claim that a model has solved the corpus; model A/B runs should use the existing pinned wrapper with this manifest only after the fixtures and hidden gates are independently reviewed.

## Interpretation

The purpose of this layer is to answer:

> Can deslop substantially reduce accumulated test and defensive machinery without breaking meaningful behavior?

It is not a line-deletion contest. `Simplification Case Recall` measures whether a case reaches its adjudicated simpler state; reduction magnitude is reported separately and only after hidden behavior gates pass.

This change deliberately does not add a plugin package, a new dependency, a second A/B orchestration framework, a holdout corpus, or automatic model-result publishing. Those belong after the focused fixtures and hidden contracts survive review.
