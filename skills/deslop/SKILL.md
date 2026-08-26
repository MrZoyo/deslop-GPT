---
name: deslop
description: Audit or apply subtractive cleanup for accumulated agent-created test bloat, verification theater, and defensive or fallback bloat while preserving independent external behavior. Invoke explicitly for semantic simplification, not generic refactoring.
---

# Deslop

Deslop removes complexity accumulated during repeated coding-agent implementation and correction cycles. It is a semantic cleanup policy, not a beautifier, dead-code sweeper, generic refactoring tool, or redesign assistant.

## Priority order

Work in this order. Do not let an easy dead-code deletion displace a higher-priority cluster.

1. **Test-suite bloat.** Treat tests as production code that can accumulate after every agent correction. Remove duplicate, self-referential, implementation-detail, and obsolete tests while retaining a minimum sufficient set of independent behavioral evidence.
2. **Verification theater.** Investigate checksums, receipts, manifests, validators, recomputation, and result envelopes whose producer and verifier share the same information and failure domain.
3. **Defensive and fallback bloat.** Investigate broad catches, catch-and-fallback paths, speculative compatibility branches, repeated validation, and recovery machinery that masks errors without a current contract.

Generic dead code, wrappers, abstractions, comments, and ordinary duplication are secondary. Touch them only when they belong to one of the three target clusters or have direct high-confidence evidence.

**Reduce test surface, not behavior surface.** Evidence that a test is redundant or accumulated test-suite bloat justifies deleting or consolidating that test; it is not independent evidence for changing the production behavior the test exercises. When test-suite bloat is the active target, keep distinct externally observable production semantics—including public success, rejection, error, edge-case, and supported compatibility behavior—outside the deletion target unless the production construct is separately justified for removal by another target cluster, or direct evidence from current requirements, real callers, specifications, or history establishes that the behavior is obsolete or incorrect. Do not reclassify tested behavior as defensive or validation bloat merely because deleting its test leaves nothing else requiring it; the test may be its clearest executable specification.

Adding tests is not the default response to cleanup. When production slop is deleted, tests whose only purpose is to protect that slop should normally be deleted in the same change.

## Closed justification loops

Production code does not justify a test merely because the test exercises it. A test does not justify production code merely because the production code exists. Follow justification chains outward until they reach an independent evidence root.

A production/test pair is mutual-support slop only when the production construct has no independently meaningful externally observable purpose. A test of a distinct externally observable rejection or error behavior is not a closed justification loop merely because the test is its clearest executable specification. Internal checksum or receipt machinery and tests created only for that machinery can form such a loop, as can a speculative fallback and tests created only to exercise it.

If a fallback exists only because a test exercises it, and that test exists only because the fallback was added, neither member is independent evidence. The same closed justification loop can include checksum logic and checksum tests, receipts/manifests and validators, wrappers and wrapper-only tests, obsolete compatibility branches and their tests, or defensive validators and tests that only exercise them. Call this **mutual-support slop**.

Accept a dependency cluster only when its chain reaches a current user requirement, real external caller, public API contract, documented protocol or specification, security/trust boundary, persistence or corruption boundary, or scientific/numerical invariant. If the cluster only justifies itself, prefer deleting the whole cluster rather than preserving each member because another member depends on it.

## Modes and authorization

Interpret invocation from natural language; do not depend on a runtime-specific arguments variable.

- **Default or `audit`:** read-only. Report candidates, evidence, confidence, closed loops, and constructs to preserve.
- **`apply`:** modify files only within the established scope.
- **`tests`:** prioritize test signal and mutual-support slop. Without `apply`, remain read-only.
- **`deep`:** inspect repository-wide. Without `apply`, remain read-only; with `apply`, cleanup is allowed but redesign is not.
- **Explicit paths:** inspect and edit those paths plus the minimum callers, contracts, and tests needed to establish independence.
- **Current branch or no scope inside Git:** use the actual merge base and include staged, unstaged, and untracked work; never assume `main`.

Only `apply` authorizes edits. Do not fetch, reset, switch branches, stage, commit, push, or create backups unless explicitly requested.

## Establish evidence before editing

1. Read applicable `AGENTS.md` files, repository conventions, and the requested scope.
2. Inspect callers, tests, history, specifications, and documented verification commands.
3. Classify the evidence chain before trusting an existing test or fallback.
4. Put current user requirements and corrections first. A current user requirement or correction overrides conflicting historical tests; do not preserve old or incorrect behavior merely because an existing test asserts it.
5. A bug fix should normally replace incorrect behavior, not preserve it behind a fallback.

Inside trusted code, use a **fail-visible bias**: allow unexpected failures to surface unless there is a concrete recovery, translation, cleanup, protocol, or compatibility contract. Broad `except Exception`, catch-and-fallback, catch-log-rethrow, speculative legacy fallbacks, and compatibility branches without independent evidence are high-priority investigation targets. Do not hide bugs in the name of robustness.

## Confidence and apply behavior

- **HIGH:** redundant, tautological, unreachable, self-justifying, or disconnected from a real contract after the evidence chain is resolved.
- **MEDIUM:** apparently unnecessary, but caller, history, compatibility, or boundary evidence is still missing.
- **LOW / PRESERVE BY DEFAULT:** security, authorization, concurrency, persistence, transactions, external protocols, supported compatibility, resource limits, and scientific invariants whose purpose may be outside the local file.

In apply mode:

- HIGH: delete or simplify once the evidence is resolved.
- MEDIUM: do not modify until the missing evidence question is resolved.
- LOW: preserve unless direct contrary evidence is established.

Apply authorization is permission to edit, not permission to resolve uncertainty in favor of deletion.

Read only the relevant references:

- [test-smells.md](references/test-smells.md) for accumulated test suites and test/production mutual-support clusters.
- [verification-and-trust.md](references/verification-and-trust.md) for checksum, receipt, manifest, provenance, and trust-boundary clusters.
- [code-smells.md](references/code-smells.md) for defensive, fallback, compatibility, wrapper, and abstraction candidates.
- [scientific-code.md](references/scientific-code.md) for numerical, simulation, ML, or engineering invariants.

## Subtractive workflow

1. Inventory tests before production cleanup. Group them by distinct externally meaningful behavior and independent oracle; keep the minimum sufficient set. Do not optimize for test count, assertion count, or coverage percentage.
2. Trace verification machinery as a cluster, not a function. Remove serialization, digest fields, envelopes, manifests, validators, recomputation, and tests together when no independent root remains.
3. Trace fallback branches to actual supported consumers and failure contracts. Prefer direct failure when the current contract says an operation should fail.
4. Delete tests that exist only to keep deleted production slop green. Add a replacement test only when deleting the old test would leave a real external behavior unprotected and an independent oracle exists.
5. Preserve real public, persistence, security, protocol, compatibility, resource, and scientific boundaries even when their code resembles a smell.

## Negative-change budget

Normally reduce structural surface area. New dependencies, abstractions, wrappers, compatibility layers, cryptographic/provenance machinery, and tests have a default budget of zero. New code is acceptable only when it preserves a real behavior while removing more accumulated slop. If a cleanup adds substantial production or test lines, stop and reconsider.

In `deep apply`, exclude generated code, vendored dependencies, `third_party` trees, migration history, lockfiles, and externally generated snapshots or artifacts unless explicitly included or demonstrably repository-owned.

## Proportional verification

Run the narrowest existing checks after each meaningful semantic group and the repository's documented final checks once when feasible. Verification should be independent of the change where possible. Do not create proof files, audit ledgers, checksum reports, or a new verification framework merely to validate a deletion. If a check cannot run, state that plainly.

## Final report

Report the inspected scope; removed test, verification, and fallback clusters; independent evidence roots; preserved boundaries; tests removed or consolidated; checks actually run; approximate production/test size changes when useful; and uncertainty intentionally left untouched. Explicitly call out any closed justification loop that drove deletion.
