# rc3 focused micro pilot — 2026-08-25

Status: internal development diagnostic; not a public performance claim. Machine-readable evidence is in [`rc3-micro-pilot-20260825.json`](rc3-micro-pilot-20260825.json).

## Configuration

- Corpus: `dev-v2-focused-rc3` at `c08cee1dd161ee193f1c5e1b019abbdd2adaa54e`
- Model: `gpt-5.6-sol`, reasoning effort `medium`
- Harness: `agent-skill-eval==0.7.0`, `codex-cli 0.149.1`
- Shape: 16 cases × baseline/deslop, one run each, 32 calls, concurrency 1
- No retries, timeouts, run errors, or skipped runs

## Automatic results

| Metric | Baseline | With deslop | Delta |
| --- | ---: | ---: | ---: |
| Simplification case recall | 5/8 (62.5%) | 8/8 (100%) | +37.5 pp |
| Behavior preservation | 4/8 (50%) | 2/8 (25%) | -25 pp |
| Full-case pass | 9/16 (56.25%) | 10/16 (62.5%) | +6.25 pp |

Paired outcomes: 7 both-pass, 3 deslop improvements, 2 deslop regressions, and 4 both-fail.

- Improvements: `t04a`, `f01a`, `f02a`.
- Regressions: `t01b`, `t03b`. Deslop deleted the empty-input rejection contract in both cases.
- Both-fail preservation cases: `t02b`, `v01b`, `v02b`, `f01b`.

## Manual review

The two deslop regressions are real contract losses, not negative-change-gate failures. Most both-fail cases also broke adjudicated behavior: supported legacy headers/versions or independently supplied verification boundaries were removed or their API shape changed.

`v01b` with deslop is a grader false-negative candidate. The agent retained independently supplied digest verification but removed the pass-through `write_artifact` fixture helper; the hidden behavior gate still called that helper. The exported automatic score remains unchanged.

Overall, the Skill made deletion substantially more reliable, especially for fallback clusters, but increased over-deletion risk on small preservation fixtures. One run per configuration is insufficient for a stability or superiority claim.

## Runtime and tokens

| Mean per call | Baseline | With deslop | Change |
| --- | ---: | ---: | ---: |
| Wall time | 107.7 s | 125.5 s | +16.5% |
| Total tokens | 120,088 | 195,811 | +63.1% |
| Non-cached input tokens | 22,107 | 33,739 | +52.6% |

The 32 calls used 5,054,387 total tokens and took 3,744.2 seconds wall-clock. Dollar cost was unavailable from the CLI telemetry.
