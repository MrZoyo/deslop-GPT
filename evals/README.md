# Active evaluation protocol

[简体中文](README.zh-CN.md) · **English**

The active development benchmark is [`dev-v2-focused`](dev-v2-focused/README.md). It targets accumulated complexity created by repeated coding-agent cycles, not generic cleanup:

- test-suite bloat: 4 paired cases (50%);
- verification theater: 2 paired cases (25%);
- defensive/fallback bloat: 2 paired cases (25%).

The 16 micro cases have same-prefix preservation counterexamples, golden/mutant polarity calibration, and alternate-valid calibration. The three mini repositories model accumulated test, verification, and fallback slop at repository scale.

`dev-v2-focused-rc5` is frozen. The separate [`dev-v3-evidence-edges`](dev-v3-evidence-edges/README.md) draft contains 19 anonymized field observations and 7 executable pairs about production reachability, test hermeticity, authoritative artifacts, and schema contracts. It is validated in CI but is not yet a model-comparison corpus; its results must not be combined with `dev-v2-focused`.

## Real-world evidence

Manually adjudicated field trials are preserved separately under `real-world/` as historical evidence. They are not currently part of the active quantitative benchmark and must not be used to tune the Skill from a single repository. See the [`cluster-gpu-monitor` case study](real-world/cluster-gpu-monitor/README.md).

## Hard-gate order

Focused grading separates four gates:

1. **Behavior gate:** current/legacy protocol behavior, public output, persistence corruption detection, security/provenance boundaries, and atomic cleanup. It must not prescribe test function count, test names, helper shape, or a historical patch.
2. **Remaining-test gate:** at least one discovered test remains and the suite passes.
3. **Reduction target:** the after-state reaches the category threshold in adjudication; deleting one token or one duplicate is not sufficient.
4. **Negative-change gate:** cleanup cannot add Python files, tests, dependencies, wrappers/abstractions, category machinery, syntax errors, or more than four positive nonblank Python lines.

For mini repositories, the remaining test suite and hidden behavior gate must both pass before any reduction metrics are eligible. A failed after-state receives no partial reduction score.

`Simplification Case Recall` is case-level semantic recall, not a percentage of lines removed. Reduction magnitude is reported separately and only for eligible states.

## Validate before any model run

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
```

The focused validator checks:

- 16 paired IDs and the 4/2/2 target mix;
- baseline tests and behavior polarity;
- golden-after and destructive-mutant polarity;
- insufficient-cleanup rejection in all three categories;
- at least two alternate-valid states in each category;
- every negative-change failure mode;
- three mini-repository behavior, reduction, and metric gates;
- the 16-case micro manifest and 3-case mini-repository manifest.

The `dev-v2-focused-rc5` revision is frozen. Do not run GPT A/B on the `dev-v3-evidence-edges-draft1` corpus while it is changing; review and freeze it before collecting comparable results. Keep the published rc3 micro and rc4 mini pilots as separate historical evidence.

## Model run shapes after freeze

The first command is the **16-case focused micro-case A/B diagnostic**:

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

The separate **three-repository end-to-end A/B** uses the same wrapper and hook:

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

The micro diagnostic does not measure whole-mini-repository cleanup. Keep the two result sets and names separate.

No result from this command is publishable without the frozen revision, model/config metadata, raw per-case gates, and a separate held-out corpus.

## Retired `dev-v1`

The broad 20-case `dev-v1` suite is no longer an active tuning benchmark. Its fixtures, old grader, protocol, and historical diagnostics remain under [`archive/dev-v1/`](archive/dev-v1/) for history and broad safety-regression reference. Active CI does not run it.
