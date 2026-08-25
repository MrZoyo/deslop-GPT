# Active evaluation protocol

The active development benchmark is [`dev-v2-focused`](dev-v2-focused/README.md). It targets accumulated complexity created by repeated coding-agent cycles, not generic cleanup:

- test-suite bloat: 4 paired cases (50%);
- verification theater: 2 paired cases (25%);
- defensive/fallback bloat: 2 paired cases (25%).

The 16 micro cases have same-prefix preservation counterexamples, golden/mutant polarity calibration, and alternate-valid calibration. The three mini repositories model accumulated test, verification, and fallback slop at repository scale.

## Hard-gate order

Focused grading separates two questions:

1. **Behavior gate:** current/legacy protocol behavior, public output, persistence corruption detection, security/provenance boundaries, and atomic cleanup. It must not prescribe test function count, test names, helper shape, or a historical patch.
2. **Reduction target:** test-surface, checksum/verification, or fallback/exception machinery actually decreased relative to the untouched fixture.

For mini repositories, the remaining test suite and hidden behavior gate must both pass before any reduction metrics are returned. A failed after-state returns `eligible_for_reduction_scoring: false` rather than a partial reduction score.

`Simplification Case Recall` is case-level semantic recall, not a percentage of lines removed. Reduction magnitude is reported separately and only for eligible states.

## Validate before any model run

```bash
python3 scripts/validate_focused_corpus.py

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/evals.json
```

The focused validator checks:

- 16 paired IDs and the 4/2/2 target mix;
- baseline tests and behavior polarity;
- golden-after and destructive-mutant polarity;
- at least two alternate-valid states in each category;
- three mini-repository behavior gates and reduction-metric fields.

Do not run GPT A/B while this corpus is being changed. The current reviewed revision is frozen as `dev-v2-focused-rc2`; treat any further grader correction as `rc3` rather than mixing scores.

## Model run shape after freeze

Use the existing pinned wrapper and focused hook from the repository root:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skill/deslop \
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

No result from this command is publishable without the frozen revision, model/config metadata, raw per-case gates, and a separate held-out corpus.

## Retired `dev-v1`

The broad 20-case `dev-v1` suite is no longer an active tuning benchmark. Its fixtures, old grader, protocol, and historical diagnostics remain under [`archive/dev-v1/`](archive/dev-v1/) for history and broad safety-regression reference. Active CI does not run it.
