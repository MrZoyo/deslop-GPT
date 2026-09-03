# Test Smells

Tests are code and can be accumulated agent slop. Test signal matters more than test volume. Preserve the minimum sufficient set of tests that protects distinct externally meaningful behavior with an independent oracle.

## Start with the oracle

Ask where the expected result came from and what failure the test would expose.

```text
independent specification / known example / external caller / protocol fixture
    -> meaningful behavior assertion

same helper / same algorithm / implementation-generated expected value / mock setup
    -> self-referential test: delete, consolidate, or find a real oracle
```

An independently implemented cross-check is useful only when it can fail differently. Repeating an implementation with different names is not independence.

## Build an evidence map

For a non-trivial suite, make the reasoning inspectable before deleting nodes:

| Test or parameter group | Current owner | Production branch | Observable result | Oracle root | Failure domain | Stronger overlap |
| --- | --- | --- | --- | --- | --- | --- |
| one row per candidate | active config, caller, protocol, or none | actual branch reached | success, rejection, error, or state | independent source | what can fail differently | test that dominates it, if any |

This can remain working notes; do not add a permanent audit artifact merely to prove cleanup. The map prevents three common errors: merging tests that have different failure semantics, retaining permutations that reach the same branch and result, and deleting production behavior merely because its only test was redundant.

One test dominates another only when it protects the same owner, branch, result, and failure domain with an equally independent or stronger oracle. A public integration test does not automatically dominate a known numerical example, corruption test, or protocol rejection. Conversely, a long snapshot does not dominate a focused test merely because it asserts more fields.

## High-priority accumulated patterns

| Pattern | Suspicious signal | Preserve when | Preferred action |
| --- | --- | --- | --- |
| Duplicate behavior tests | Same input, path, and meaningful outcome with no distinct failure mode | Each test protects a separate contract or historical regression | Keep the strongest readable test |
| Successive regression-test accumulation | A new near-identical test was added after every minor agent/user correction | Each correction protects a genuinely different externally visible bug | Collapse to the minimum distinct regression set |
| Duplicate integration coverage | Several tests traverse the same public path and oracle | Different boundary, failure class, or supported environment is exercised | Remove redundant scenarios |
| Parameter-permutation bloat | Values vary without changing a branch, equivalence class, invariant, or risk | The permutation represents a real boundary or failure mode | Keep representative cases |
| Aggregate-plus-item duplicate | `all(...)`, count, or length restates stronger per-item behavior checks | The aggregate is a distinct collection-level contract | Delete the weaker assertion |
| Weak type/None/length/existence check | Assertion is dominated by a stronger behavior assertion in the same test | Presence, type, or cardinality is itself public contract | Remove or keep only the independent contract |
| Private-helper test | Test exists because an agent extracted a helper already covered through a public seam | Helper has a stable, independently specified algorithm | Delete with the helper or test publicly |
| Implementation-detail test | Private state, helper call, exact temporary object, or harmless ordering is asserted | Detail is a protocol, transaction, concurrency, lifecycle, or resource contract | Assert the meaningful seam |
| Exact call-count test | Count follows current implementation mechanics | Count controls billing, retry, batching, idempotency, or a documented limit | Assert external effect unless count is semantic |
| Exact sequencing test | Harmless refactor breaks the expected order | Order is required by protocol, locks, transactions, or cleanup lifecycle | Keep only semantic ordering |
| Mock-verifies-mock | Mock setup dictates output and verification repeats setup | Interaction with an unavailable boundary is the real contract | Reduce mocking and assert boundary behavior |
| Wrapper-only test | Test protects a pass-through wrapper with no policy or boundary | Wrapper is a published API, external integration, or lifecycle seam | Remove wrapper and test together |
| Defensive-machinery test | Test exists only for a validator, fallback, receipt, checksum, retry, or self-check that is itself suspect | Machinery has an independent surviving contract | Delete the mutual-support cluster |
| Implementation-derived expected value | Expected value is recomputed by the code under test or a copied algorithm | Independent reference data or mathematical invariant exists | Use the independent oracle or delete |
| Snapshot bloat | Large snapshots obscure a small behavioral signal | Rendered/serialized artifact is the externally reviewed contract | Replace with focused semantic assertions |
| Fixture-tautological test | Fixture setup guarantees the asserted state and no production behavior is invoked | Fixture state is an independently established integration precondition | Delete |
| Obsolete-behavior test | Test preserves behavior a current user requirement explicitly corrected | Supported consumers still require the old behavior | Replace the test with the corrected contract |
| Unmanaged-artifact test | Default tests read untracked `outputs/`, a one-off run directory, or a local formal package | Input is repository-managed, test-created, or an explicitly provisioned external resource | Delete the orphan test/support cluster or rebuild a self-contained behavioral test |
| Tracked-output test | A compiler or materializer reached through a test writes to a tracked target | The test redirects writes to a temporary path and treats tracked data as read-only input | Redirect the output; inspect deep builders, not only direct file writes |
| Synthetic-capability test | A production dry-run invents observations or success states and a test asserts that scripted success | Dry-run only parses, assembles, or validates without claiming the backend capability | Delete the fake capability path and its test |
| Fake-only dependency skip | A fake-backed test skips when an SDK or simulator it never calls is absent | The test actually imports, compiles, encodes, or calls the optional boundary | Remove the skip or use one consistent module-level boundary |
| Disconnected layer tests | Producer, loader, and consumer pass separately, but no test crosses the current identity through all three | A hermetic integration root already protects that production edge | Keep or create the smallest independent current-path root before retiring the old fixture |
| Coverage-owned branch test | A threshold mutation, future-only config, or direct post-gate helper call exists only to cover a branch | Active production input reaches the branch or an adjacent guard has distinct safety semantics | Remove the unreachable branch/test cluster after checking current configs and registries |

## Closed justification loops

Production code does not justify a test merely because the test exercises it. A test does not justify production code merely because the production code exists. Trace test -> production branch -> reason -> external evidence.

If a test exists only to keep a defensive branch green, and the branch exists only because that test was added, the pair is mutual-support slop. Apply the same rule to checksum tests and digest code, receipt tests and receipt validators, wrapper tests and wrappers, compatibility tests and obsolete branches, and validator tests and validators. Do not preserve one member merely because the other member depends on it; delete the closed cluster when no independent root remains.

Independent roots include a current user requirement, real external caller, public API, documented protocol, security or trust boundary, persisted corruption boundary, scientific invariant, or a separately maintained reference dataset.

## Keep or delete

For every test, answer:

1. What distinct behavior or plausible regression does it protect?
2. Would it fail if that behavior regressed?
3. Is the oracle independent from the implementation and its support machinery?
4. Is stronger coverage already present?
5. Does it observe a public or meaningful boundary?
6. Would a harmless refactor break it while behavior stayed identical?
7. Was it added only after a local correction, without a new failure mode?

Delete or consolidate when no distinct regression remains. Preserve separate tests for distinct contracts, failure semantics, security properties, persistence/transaction behavior, concurrency, supported compatibility, resource limits, scientific invariants, known numerical results, and real prior regressions.

Do not optimize for test count, assertion count, branch coverage, or line coverage. A smaller suite with independent signal is better than a larger suite that merely documents its own implementation.

## Retire fixtures by behavior

An obsolete fixture and the behavior once reached through it are separate decisions. Map every fixture-backed test to a current owner. Delete behavior with no owner; move surviving behavior to the lowest stable public seam. Before removing a cross-layer fixture, confirm that one hermetic test still crosses the current producer, reader, and consumer. Green endpoint unit tests do not prove that edge.

Delete a fixture's private builders, fakes, compatibility fields, and helper stack when no surviving test or production path uses them. Do not restore an unmanaged experiment artifact or preserve a whole legacy package merely to keep one current assertion reachable.

## Adding tests during cleanup

Adding a test is not the default response. Add one only when:

- a real externally meaningful behavior is otherwise unprotected;
- the behavior is genuinely uncertain after reading callers, contracts, and history;
- a plausible regression would fail the test;
- the expected result has an independent source; and
- the test observes a meaningful seam rather than cleanup details.

When production slop is deleted, delete tests whose only purpose was to protect that slop in the same change. Do not add a replacement test merely because a function now lacks a unit test, coverage falls, or a model prefers symmetry. A current user requirement or correction outranks a historical test that asserts obsolete or incorrect behavior.

## Consolidation discipline

- Prefer one readable test per distinct behavior, not one per branch or helper.
- Parameterize only genuine equivalence classes; do not hide an opaque generated matrix.
- Keep scenario names and failure messages capable of localizing a real regression.
- Run the remaining suite after deletion; zero remaining tests is not a passing cleanup.
- Preserve low-level tests when low-level behavior itself is a stable contract, not merely because the code is private.
- Count collected nodes before and after, then inspect skips and deselections; a smaller reported total can hide lost execution.
- Fingerprint the worktree around suites that invoke compilers, materializers, exporters, or code generators.

For generated inputs, current configuration, and cross-layer path checks, also read [evidence-and-reachability.md](evidence-and-reachability.md).
