# rc4 mini-repository pilot — 2026-08-25

Status: internal development diagnostic; not a public performance claim. Machine-readable evidence is in [`rc4-mini-pilot-20260825.json`](rc4-mini-pilot-20260825.json).

## Configuration

- Corpus: `dev-v2-focused-rc4` at `54dca4e4bcaf53616ea93fed4428023ca99171d1`
- Model: `gpt-5.6-sol`, reasoning effort `medium`
- Harness: `agent-skill-eval==0.7.0`, `codex-cli 0.149.1`
- Shape: 3 mini repositories × baseline/deslop, one run each, 6 calls, concurrency 1
- No retries, timeouts, run errors, or skipped runs

The first rc3 mini attempt exposed the nested-workspace grading bug and is excluded. rc4 changed only the mini post-grade workspace path.

## Automatic results

| Repository | Baseline | With deslop |
| --- | ---: | ---: |
| Test bloat | PASS | PASS |
| Verification bloat | FAIL | PASS |
| Fallback bloat | PASS | PASS |
| Total | 2/3 (66.7%) | 3/3 (100%) |

## Reduction evidence

- Test bloat: both configurations reduced 26 → 1 tests, 73 → 11 test LOC, and 19 → 0 fixture invocations. Production LOC fell 15 → 13.
- Verification bloat: both reduced 3 → 1 tests and 3 → 1 hash operations while preserving the external persisted-readback digest. Baseline reduced production LOC by 5 and test LOC by 9; deslop reduced them by 6 and 9.
- Fallback bloat: both removed the parser catch-and-return fallback while preserving versioned compatibility and atomic cleanup. Baseline changed production/test LOC by -7/+1 and kept 5 tests; deslop changed them by -9/-2 and reduced 5 → 4 tests.

## Manual review

The formal verification-bloat uplift is a grader false negative, not reliable product evidence. Baseline removed the self-generated digest, receipt, and validator and retained the independent readback digest, but used `envelope` as the name of a plain records mapping. The lexical `local_verification_surface` metric rejected that name even though behavior and remaining tests passed.

After manual semantic adjudication, both configurations solved all three mini repositories. Deslop was more subtractive in verification and fallback, but the single-run mini pass rate does not establish a robust model-effect claim.

## Runtime and tokens

| Mean per call | Baseline | With deslop | Change |
| --- | ---: | ---: | ---: |
| Wall time | 114.1 s | 151.6 s | +32.9% |
| Total tokens | 146,657 | 202,557 | +38.1% |
| Non-cached input tokens | 43,203 | 33,219 | -23.1% |

The 6 valid calls used 1,047,642 total tokens and took 802.5 seconds wall-clock. Dollar cost was unavailable from the CLI telemetry. No raw trajectories, stdout, or reasoning traces are published.
