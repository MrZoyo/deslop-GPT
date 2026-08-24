# deslop `dev-v1` c01a Repeated Codex A/B

Status: internal diagnostic only. This is not a public performance claim.

## Reproduction

- Repository commit: `03325d2b4433ee4747e47656ea80126af1c4e75f`
- Run window: `2026-08-24T19:38:18Z` to `2026-08-24T19:46:35Z` (`2026-08-25` in Asia/Shanghai)
- Runtime Skill evaluated in this historical run: `skill/deslop/`
- Skill content hash at run time: `13f9de264fd14d8f55f774a47aab93cb25ed45572708c588cebabf7b5bd0b527`
- Skill payload at run time: 6 files, 33,063 bytes, 4,184 words
- Harness: `agent-skill-eval==0.7.0`
- Agent CLI: `codex-cli 0.149.0`
- Model: `gpt-5.6-sol`
- Reasoning effort: `medium`
- Case: `c01a`
- Runs: 3 per configuration; 6 model calls total
- Concurrency: 1; retries: 0; timeout: 900 seconds
- Sandbox: `workspace-write`
- Network: not explicitly pinned or recorded by the harness
- Approval/config: Codex CLI defaults and local profile inherited except the pinned model and reasoning effort

The user-level `$HOME/.agents/skills/deslop` directory was moved out of discovery for the run and restored by an exit trap. Every with-Skill run verified `.agents/skills/deslop` and the content hash above.

The baseline received the same strong evidence-backed cleanup prompt without `$deslop`. This experiment measures incremental Skill value over that prompt, not over an unprompted or generic Codex session.

## Run outcomes

| Configuration | Run 1 | Run 2 | Run 3 | Full-pass rate | `pass@3` |
| --- | --- | --- | --- | ---: | ---: |
| Without Skill | FAIL | PASS | FAIL | 1/3 (`0.333`) | 1.0 |
| With Skill | PASS | FAIL | PASS | 2/3 (`0.667`) | 1.0 |

Both configurations are flaky on `c01a`. The observed full-pass difference is one run and is not sufficient evidence for a stable Skill improvement.

The new non-scored diagnostics were consistent:

- Every passing run removed `first_record`, `json_equal_via_digest`, and `hashlib`, while preserving `load_episode` behavior.
- Every failing run retained both top-level helpers, removed the `hashlib` dependency and nested digest implementation, and preserved `load_episode` behavior.
- All six runs passed the remaining unittest suite, side-effect contract, and negative-change budget.

This confirms that the original one-run `c01a` failure was stochastic rather than a deterministic inability of either configuration. It also shows a stable partial-cleanup mode: stop after removing hashing machinery while preserving the two top-level entry points.

## Aggregate metrics

| Metric | Without Skill | With Skill | Delta (with − without) |
| --- | ---: | ---: | ---: |
| Mean assertion pass rate | 0.833 | 0.917 | +0.083 |
| Full-pass rate | 0.333 | 0.667 | +0.333 |
| `pass@3` | 1.0 | 1.0 | 0.0 |
| Mean wall time | 73.932 s | 90.734 s | +16.803 s |
| Mean total tokens | 106,656 | 158,104 | +51,448 |
| Mean cached input tokens | 82,432 | 134,229 | +51,797 |
| Mean non-cached input tokens | 22,229 | 21,230 | −998 |
| Mean completed command executions | 5.33 | 9.00 | +3.67 |
| Mean agent messages | 4.67 | 5.67 | +1.00 |

Across all six calls: 794,279 total tokens, 780,361 input tokens, 649,984 cached input tokens, 130,377 non-cached input tokens, 13,918 output tokens, and 3,802 reasoning tokens. Cost is unavailable because the Codex CLI reported no cost and no pricing configuration was supplied.

Most of the mean total-token difference came from cached input; mean non-cached input was slightly lower with Skill in this small sample. The with-Skill runs also completed more commands, so the observed overhead cannot be attributed to instruction bytes alone.

## Interpretation

The repeated result is directionally favorable to the Skill on this one development case, but both configurations are flaky and `n=3` is too small for an effectiveness claim. The result does not justify adding a new Skill rule solely to force a second sweep. The next useful experiment is the one-run full `dev-v1` diagnostic to identify whether the Skill improves, regresses, passes, or fails across the wider case distribution.

The full-pass rate is more informative here than mean assertion pass rate because the other three gates passed in every run. `pass@3` is identical and only establishes that both configurations can solve the case at least once.

## Evidence

A sanitized transcript-free record is stored in [`dev-v1-c01a-repeat-20260825.json`](dev-v1-c01a-repeat-20260825.json). Raw local artifacts remain under:

`eval-workspace/deslop-c01a-repeat/deslop-workspace/iteration-1/`

The machine-readable record includes per-run timing, grading, diagnostics, structural deltas, Skill discovery, and trajectory event counts without model reasoning or conversation text.
