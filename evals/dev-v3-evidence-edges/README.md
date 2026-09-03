# `dev-v3-evidence-edges` draft

[简体中文](README.zh-CN.md) · **English**

This follow-up corpus turns an anonymized 2026-09-02 field review into paired evidence-boundary cases. It does not change or rescore the frozen `dev-v2-focused-rc5` fixtures, graders, or results.

The same review also informed the accompanying Skill rules, so this is an exposed development regression corpus, not held-out evidence of Skill effect. Any model-effect claim requires a separate uncontaminated corpus.

## What is included

The source review contains 19 positive/negative observations in [`evidence-bank.json`](evidence-bank.json). Here, **positive** means that evidence supports subtraction or a fail-visible correction; **negative** means that a nearby construct has an independent root and must be preserved.

Seven executable pairs cover nine of the observations in this draft:

| Pair | Category | Positive target | Negative boundary |
| --- | --- | --- | --- |
| `r01` | Production reachability | Remove a branch reachable only through a synthetic test flag | Preserve variants selected by active production configuration |
| `r02` | Path closure | Retire an obsolete package fixture and its private path | Keep one hermetic current producer-to-consumer integration root |
| `h01` | Test hermeticity | Remove a skipped test that depends on an unmanaged run artifact | Preserve a repository-managed protocol fixture |
| `h02` | Test hermeticity | Redirect a builder test away from a tracked output | Preserve tracked source data used read-only with temporary output |
| `v03` | Artifact authority | Make a declared authoritative artifact required and verified | Preserve explicitly optional enrichment behavior |
| `s01` | Schema contract | Make every current public reader reject an old schema | Preserve an explicit migration reader for the old schema |
| `s02` | Schema contract | Remove a historical default for a required identity field | Preserve a documented default for optional presentation data |

Five observations remain in the candidate layer: snapshot scope, manufactured dry-run success, registry/CLI ownership loops, fake-only dependency skips, and stale current documentation. The bank also records five patterns already covered by `dev-v2-focused` and groups the safety, persistence/protocol, and hardware/numerical failure domains that cleanup must preserve.

## Actions and gates

Each `a` case requires either `simplify` or `repair`; each nearby `b` case protects a preservation boundary. Grading keeps four decisions separate:

1. **Current behavior:** valid public behavior still works.
2. **Remaining tests:** at least one discovered test remains and the suite passes.
3. **Target:** the unjustified surface is gone or the fail-open contract is corrected.
4. **Negative-change budget:** no new files, tests, dependencies, or abstractions, and only small action-specific Python growth is allowed.

Every positive case has a `golden_after` calibration. Every preservation case has a `destructive_mutant` that leaves ordinary tests green where practical but fails the hidden boundary. The draft also contains alternate-valid and insufficient-cleanup states for patch-shape and threshold checks.

## Validate the draft

Run the dependency-free validator:

```bash
python3 scripts/validate_evidence_edges_corpus.py
```

After installing the pinned harness dependency, validate the manifest:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v3-evidence-edges/evals.json
```

Do not use this draft for model comparisons yet. Freeze a revision, review the hidden contracts for leakage and patch specificity, then collect a fresh baseline. Results from this corpus must remain separate from `dev-v2-focused` micro and miniature-repository results.
