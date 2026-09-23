# `dev-v3-evidence-edges` draft

[简体中文](README.zh-CN.md) · **English**

This follow-up corpus turns an anonymized 2026-09-02 field review into paired evidence-boundary cases. Draft2 added a narrow follow-up from the 2026-09-23 GPT-6 Sol xhigh cleanup review; draft3 added one pair from the same-day Opus 5.5 A/B (session-level xhigh). The current `dev-v3-evidence-edges-draft4` incorporates the release review below. It does not change or rescore the frozen `dev-v2-focused-rc5` fixtures, graders, or results.

The same review also informed the accompanying Skill rules, so this is an exposed development regression corpus, not held-out evidence of Skill effect. Any model-effect claim requires a separate uncontaminated corpus.

## What is included

The source review contains 19 positive/negative observations in [`evidence-bank.json`](evidence-bank.json). Here, **positive** means that evidence supports subtraction or a fail-visible correction; **negative** means that a nearby construct has an independent root and must be preserved.

Seven field-derived pairs cover nine of those observations; two cleanup-review pairs bring the draft to nine pairs (18 cases). The original 19-observation bank is unchanged.

| Pair | Category | Positive target | Negative boundary |
| --- | --- | --- | --- |
| `r01` | Production reachability | Remove a branch reachable only through a synthetic test flag | Preserve variants selected by active production configuration |
| `r02` | Path closure | Retire an obsolete package fixture and its private path | Keep one hermetic current producer-to-consumer integration root |
| `h01` | Test hermeticity | Remove a skipped test that depends on an unmanaged run artifact | Preserve a repository-managed protocol fixture |
| `h02` | Test hermeticity | Redirect a builder test away from a tracked output | Preserve tracked source data used read-only with temporary output |
| `v03` | Artifact authority | Make a declared authoritative artifact required and verified | Preserve explicitly optional enrichment behavior |
| `v04` | Artifact authority | Remove a local proof chain and forwarding body while retaining public write/read operations | Preserve required manifest fields, independent content checks, and atomic writer cleanup |
| `s01` | Schema contract | Make every current public reader reject an old schema | Preserve an explicit migration reader for the old schema |
| `s02` | Schema contract | Remove a historical default for a required identity field | Preserve a documented default for optional presentation data |
| `v05` | Artifact authority | Remove a self-only fingerprint cluster while keeping one test rooted in the surviving public result | Preserve a producer-computed fingerprint that an independent publisher recomputes and enforces |

Five observations remain in the candidate layer: snapshot scope, manufactured dry-run success, registry/CLI ownership loops, fake-only dependency skips, and stale current documentation. The bank also records five patterns already covered by `dev-v2-focused` and groups the safety, persistence/protocol, and hardware/numerical failure domains that cleanup must preserve.

## Draft2 cleanup follow-up

The local cleanup review exposed public-writer deletion, missing manifest-size coverage, correction-specific source scans, and false failures from rigid growth/word-count rules. These are development inputs, not a new model result:

- `r02a` now includes an explicit retirement/correction record and a leftover source-absence test. Its two insufficient states distinguish deleting only the old tests from deleting the old production path but retaining a mechanical absence test. `r02b` and `s01b` continue to protect current integration and supported migration.
- `v04a` preserves two public writer names and the reader while removing private self-proof code. Both alias directions are valid, and either one combined test or two public-operation tests can pass.
- `v04b` independently checks wrong and missing size, wrong and missing digest, same-length corruption, both public writer names, and write/replace failure cleanup. Five destructive states keep their ordinary suites green while violating one of these contracts.
- The `v04b` alternate replaces a pre-write-only failure with a partial write and adds same-length corruption inside the existing tests. It adds seven nonblank lines with no new test node or hash operation. Its declared eight-line allowance is confined to this case; the validator proves that the stronger suite catches digest and cleanup faults the original suite misses. No checksum-word budget is used in v3.

This does not revise old scores or establish a model-performance improvement. Draft2 remains exposed regression material; freeze and separately evaluate it before making comparative claims.

## Draft3 Opus 5.5 follow-up

A 2026-09-23 Opus 5.5 A/B on the then-current payload, run and archived outside the checkout, exposed a regression pattern in the Skill arm on `dev-v2-focused`: in `v01a` and `v02a` it removed the self-verification cluster together with every test, ending at zero discoverable tests, while the baseline kept one test of the surviving public function. Two `repair` cases lacked rejection assertions; a third used a reader loop that the grader did not recognize. `v05` turns the first pattern into a pair. Each arm ran once per case, and effective subagent effort was not independently verified, so these observations do not isolate the causal effect of a particular instruction.

- `v05a` has a public `render_manifest` whose only tests exercise a self-only fingerprint and verifier. Its contract records that nothing consumes the fingerprint. The target requires the hash and helper to be gone and one test to still call `render_manifest`. A `zero_tests` calibration state records the rejected outcome: behavior intact, target machinery gone, no discoverable test. The validator requires that state to discover no tests, so the remaining-test gate is what rejects it, and `insufficient_cleanup` keeps the fingerprint field with its field-presence test.
- `v05b` has the same code shape, but its contract names an independent publisher that recomputes the canonical fingerprint and rejects mismatches, and its test pins the published literal. Two destructive states keep ordinary tests green while dropping the field or the canonical serialization.

These are development inputs, not a model result. Draft3 is still exposed regression material.

## Draft4 release review

- `h01a` now supplies an explicit retirement contract. Missing local callers alone must not justify deleting a public function.
- The rejection-coverage check accepts literal groups of readers inside `assertRaises`; an alternate `s01a` calibration preserves both readers' behavior with that layout. It is still a bounded static check, not general proof of test coverage.
- `v05a` checks removal of the actual fingerprint field, so a harmless explanatory docstring does not cause a keyword-based failure.
- Runtime guidance preserves independent coverage without requiring rejection assertions to share a success-test node or inventing expected values to avoid a zero count.

Historical A/B grades remain unchanged. Draft4 has offline calibration only and is not a fresh model comparison.

## Actions and gates

Each `a` case requires either `simplify` or `repair`; each nearby `b` case protects a preservation boundary. Grading keeps four decisions separate:

1. **Current behavior:** valid public behavior still works.
2. **Remaining tests:** at least one discovered test remains and the suite passes.
3. **Target:** the unjustified surface is gone or the fail-open contract is corrected.
4. **Negative-change budget:** no new files, tests, dependencies, or abstractions, and only small action-specific Python growth is allowed. The sole case-specific allowance is the calibrated `v04b` coverage repair described above; unrelated growth is still bounded.

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
