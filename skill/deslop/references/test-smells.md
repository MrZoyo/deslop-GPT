# Test Smells

Tests are code and can be slop. Test signal > test volume. Preserve tests that protect distinct externally meaningful behavior; delete or consolidate tests that only increase brittleness.

## Oracle Independence

First ask where the expected result came from.

```text
Is the expected value derived independently?
|
+-- Yes: specification, known example, analytical result, protocol fixture,
|        external behavior, or separately stated invariant
|   `-- Continue evaluating distinct behavior and regression value
|
`-- No: same helper, constants, algorithm, generator, mock arrangement,
         or output produced by the implementation under test
    `-- The test is probably self-referential; replace or delete it
```

An independently implemented cross-check can be valuable when independence is intentional and the two implementations do not share the same failure mode. Mere duplication does not create an oracle.

## Smell Checklist

| Smell | Evidence for deletion or consolidation | Preserve when | Preferred action |
| --- | --- | --- | --- |
| Duplicate behavior tests | Inputs, path, and meaningful outcome match stronger coverage | Case represents a distinct contract or regression | Delete the weaker duplicate |
| Duplicate assertions | Assertions restate the same postcondition or static type fact | Each assertion protects a distinct contract facet | Keep the strongest direct assertion |
| Tautological assertion | Compares a value with itself or cannot fail under setup | Framework integration can genuinely alter it | Delete |
| Self-referential oracle | Expected result uses production helper, algorithm, generator, or constants | Intentional independent implementation | Use a known external result or delete |
| Weak existence/type test | Only asserts non-nullness, type, or meaningless length | Presence or type is itself a documented contract | Replace with a meaningful result assertion |
| Implementation-detail test | Asserts private state, helper calls, temporary objects, or harmless ordering | Detail is a protocol, transaction, concurrency, or lifecycle guarantee | Observe a meaningful seam |
| Private-helper test | Exists because an agent extracted a helper already covered publicly | Helper has a stable independent algorithmic contract | Delete with the helper or test through public behavior |
| Mock-verifies-mock | Setup dictates output and assertions repeat the setup | Interaction with an unavailable boundary is the actual contract | Reduce mocking and assert the boundary outcome |
| Exact call-count test | Count follows current implementation mechanics | Count controls billing, retries, batching, limits, or idempotency | Assert external effect unless count is semantic |
| Internal sequencing test | Harmless refactor changes expected order | Order is required by protocol, lock, transaction, or resource lifecycle | Keep only semantic ordering |
| Wrapper test | Protects a pass-through layer with no independent behavior | Wrapper is a stable public or integration boundary | Delete wrapper and test together |
| Defensive-machinery test | Exercises redundant validation, fallback, receipt, tamper flag, or self-check | Machinery has a surviving real contract | Delete with the machinery |
| Generated-output identity test | Generator output is compared with itself or its own snapshot | Artifact is a stable externally reviewed contract | Assert the external schema or behavior minimally |
| Snapshot bloat | Large snapshot changes under harmless edits and hides signal | Serialized or rendered artifact is the contract | Replace with focused semantic assertions |
| Parameter permutation bloat | Cases add no branch, boundary, invariant, or failure mode | Cases represent real equivalence classes | Keep representatives or readable parameterization |
| Characterization accumulation | Tests freeze accidental behavior solely because cleanup feels risky | Behavior is externally consumed or a known regression | Delete; do not manufacture a contract |
| Repeated setup-heavy tests | Many functions repeat setup for one behavior | Separate scenarios clarify distinct contracts | Consolidate without hiding important cases |
| Fixture-tautological test | Test asserts a new temporary directory is empty or another fact guaranteed solely by its own fixture, without invoking production code | Fixture state is an integration precondition established by production setup | Delete it |
| Aggregate-plus-item duplicate | `all(...)` repeats checks immediately made per item with stronger diagnostics | Aggregate enforces a different collection-level invariant | Keep the per-item assertions |

## Keep or Delete

For each test, answer:

1. What distinct behavior or plausible regression does it protect?
2. Would the test fail if that behavior regressed?
3. Is its oracle independent from the implementation?
4. Is stronger coverage already present?
5. Does it observe a public or meaningful seam?
6. Would a harmless refactor break it while behavior stayed identical?

Delete or consolidate when no distinct regression remains. Keep separate tests for different contracts, failure semantics, security properties, numerical invariants, supported compatibility, or well-defined prior regressions.

## Consolidation

- Prefer one test per distinct behavior, not one per branch or helper.
- Parameterize genuine equivalence classes only when the shared expectation stays readable.
- Do not replace many obvious tests with an opaque generated matrix.
- Keep failure messages and scenario names informative enough to localize a real regression.
- When production machinery is deleted, delete its tests rather than preserving the machinery to keep them green.

## Adding Tests During Cleanup

Adding tests is not the default. Add the smallest test only when every condition holds:

1. behavior preservation is genuinely uncertain;
2. no existing test protects that distinct external behavior;
3. a plausible regression would fail the test;
4. the expected result has an independent source;
5. the test observes a meaningful seam rather than cleanup details.

Never add a test merely because code changed, coverage might rise, or a function lacks a unit test. A cleanup that removes 100 lines and adds 150 lines of tests usually failed its objective.

## Preserve by Default

Preserve concise tests for public behavior, external protocols, security boundaries, persistence and transactions, concurrency, supported compatibility, resource limits, scientific invariants, known numerical results, and real regressions. Low-level tests are justified when low-level behavior is itself a stable contract.

Historical regressions are strong evidence only when the test protects the actual bug contract. Do not keep a nearby type, echo, or existence assertion merely because it was added in the same patch.
