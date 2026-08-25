# `dev-v2-focused-rc3` pre-freeze review

Review revision: rc3 candidate prepared from `8d36fb5` after the rc2 maintainer review. Status: calibration-complete but not yet frozen; maintainer sign-off is required before the first model run.

## Case-by-case review

| Pair | Deletion target | Preservation root | Alternate-valid check | Review result |
| --- | --- | --- | --- | --- |
| `t01` | duplicate count/type/length/None tests around one public summary | publication success and empty-input rejection | n/a for deletion; preservation shape may consolidate | behavior is external; test surface is a separate target |
| `t02` | direct private-helper test | current and documented legacy headers | one table-driven header test | private test is not required for behavior |
| `t03` | successive tests for the same normalized slug | empty rejection and Unicode casefold | one table-driven edge test | distinct edge contracts remain independent |
| `t04` | wrapper-only rendering tests and pass-through layer | `USR/1` external wire format | n/a for deletion; exact wire bytes are the root | wire boundary is not generic wrapper bloat |
| `v01` | locally generated report checksum/validator cluster | externally supplied artifact digest | alternate digest implementation | local self-check and external artifact check are separated |
| `v02` | local receipt/recomputation cluster | persisted package corruption against an external manifest | alternate digest/size order | readback failure domain remains |
| `f01` | broad current-parser catch to obsolete line parser | explicit version 1 legacy protocol | table-driven version cases | malformed current input fails visibly |
| `f02` | generic missing-name fallback | atomic write partial-file cleanup | `finally`-based cleanup implementation | recovery is preserved only where cleanup is concrete |

The `a` case behavior contracts do not require a test count, test name, helper shape, checksum absence, or fallback implementation shape. Their separate adjudication thresholds require at most one sufficient test, zero local verification surface, or zero fallback control flow. The `b` case behavior contracts check externally meaningful outcomes only. `t03a`, `v01a`, and `f01a` each have an `insufficient_cleanup` state that preserves behavior and removes some target surface but must fail reduction.

All 16 micro cases also receive the same negative-change hard gate: no new Python files, dependencies, tests, abstractions, category machinery, or syntax errors, with at most four positive nonblank Python lines. The four-line allowance is calibrated by the existing table-driven preservation alternatives.

## Mini-repository review

### `test-bloat`

The repository has a public report output, a stronger end-to-end assertion, and three simulated correction cycles adding count/type/None/length/private-helper/regression tests across four test classes/files. Repeated calls to deterministic `load_records_fixture()` make fixture invocation count observable without timing sleeps. The hidden gate checks the published summary, while metrics can report test LOC/count/runtime reduction. No private helper is treated as a behavior root.

The model reduction gate requires test count, test LOC, and fixture invocations to each fall by at least half. The known-good golden reduces fixture invocations from 19 to 1.

### `verification-bloat`

The repository contains a self-generated checksum, envelope, receipt, recomputation validator, and tests for those layers. The hidden gate uses a separately stated digest for persisted readback and corruption, so removing local theater cannot satisfy the gate by itself.

### `fallback-bloat`

The repository contains repeated validation, a catch around current parsing, a narrow versioned legacy protocol, and atomic partial-file cleanup. The hidden gate requires current and legacy protocol behavior, visible malformed-input failure, and cleanup after encoder failure. The broad catch is a reduction target; the protocol and cleanup are preservation roots.

## Review invariants

- behavior gate and reduction target are separate assertions;
- remaining tests must pass before mini-repo reduction metrics become eligible;
- untouched and insufficient-cleanup states cannot satisfy reduction;
- cleanup-induced additions are a hard failure for micro and mini runs;
- each mini-repo has a known-good `golden_after` calibration with category-specific metric reduction;
- `mini-evals.json` runs all three mini repositories through the existing wrapper and `compare_mini_repositories()` post-grade path;
- at least two `alternate_valid` overlays exist in each category (`t02/t03`, `v01/v02`, `f01/f02` preservation variants);
- `dev-v1` is archived and is not an active tuning target;
- no model A/B run has been performed for `dev-v2-focused`.

Maintainer sign-off should confirm the adjudicated thresholds, four-line negative-growth tolerance, and separate names for the 16-case micro diagnostic and three-repository end-to-end experiment. Tag the reviewed commit as `dev-v2-focused-rc3`; do not mix results from rc2 or an uncommitted working tree.
