# Design

[简体中文](design.zh-CN.md) · **English**

`deslop` is a semantic cleanup policy for complexity accumulated through repeated coding-agent implementation and correction cycles. The self-contained runtime [`SKILL.md`](../skills/deslop/SKILL.md) is authoritative; this document explains the model without duplicating every runtime instruction.

## Deletion-first, not deletion-maximal

The objective is the smallest focused subtraction that removes unjustified machinery while preserving externally meaningful behavior. Line deletion, test count, assertion count, and coverage percentage are not goals by themselves.

The three primary target clusters are:

1. accumulated test-suite bloat;
2. verification theater;
3. defensive and fallback bloat.

Generic formatting, broad refactoring, framework migration, architectural redesign, and style humanization are outside this purpose.

> **Reduce test surface, not behavior surface.**

## Test-first cleanup

When tests are in scope, audit them before changing production behavior. Map each test to its current owner, production branch, observable result, independent oracle, and failure domain. Consolidate tests only when those elements match; similar syntax or a shared helper is not enough.

Choose the strongest evidence root for each failure domain. Prefer a public seam, retain independently specified low-level invariants, and keep one hermetic integration root for each current delivery path. Treat fixtures, fakes, helper stacks, unmanaged inputs, tracked output targets, skips, and deselection rules as part of the test cluster.

Deleting redundant test evidence does not authorize deleting the behavior it observed. Production removal needs separate caller, contract, history, and reachability evidence. After cleanup, re-collect the suite, explain skips or deselections, and confirm that test execution leaves the worktree unchanged.

## Independent evidence roots

A construct is justified when its dependency chain reaches evidence independent from the construct itself. Useful roots include:

- an explicit requirement or correction in the current task, or a current authoritative project document;
- a real external caller;
- public success, rejection, error, or compatibility behavior;
- a protocol, specification, or persisted format;
- a security, authorization, transaction, or corruption boundary;
- a resource, concurrency, scientific, or numerical invariant;
- an independently supplied artifact, manifest, identity, or expected result.

Implementation similarity and historical presence are not evidence roots. Neither is the fact that an agent wrote or tested the code.

## Closed justification loops

Production code does not justify a test merely because the test exercises it. A test does not justify production code merely because the code exists.

A closed loop can contain more than a production/test pair:

```text
producer → receipt → validator → validator-only test
    ↑                                  │
    └──────── no outside consumer ─────┘
```

If the cluster has no independent root, the whole cluster is a deletion candidate. If an external consumer, protocol, persisted boundary, or independent oracle exists, the loop is open and the relevant behavior must be preserved.

## Evidence graphs include edges

Passing unit tests for a producer, reader, and consumer do not prove that the current production identity crosses all three. Before retiring a cross-layer fixture, validator, registry entry, or wrapper, trace the active config or external input through the complete public path. Preserve one hermetic integration root when deleting the old carrier would otherwise leave that edge unprotected.

Production reachability must start outside tests. A synthetic flag, future-only config, monkeypatched gate, diagnostic command, or scripted success path shows executability, not current ownership. Active configuration, an external caller, a persisted record, or an owned runtime selection establishes reachability.

## Hermetic tests and explicit authority

Permanent tests use repository-managed or test-created inputs and write generated output to temporary targets. Reading a tracked source asset can be legitimate; allowing a deep builder to overwrite a tracked compiled target is not. Optional-dependency skips should correspond to a dependency that the test actually invokes.

Requiredness comes from the protocol, not from filesystem presence. If a package declares an authoritative artifact, its absence must fail just as a digest mismatch does. If a schema changes, every current public reader must enforce the shared version; only explicitly scoped migration readers should accept the old form. Critical identity fields must be required consistently by the type, parser, and validator.

## Production/test asymmetry

Tests are evidence about behavior, not automatic owners of behavior. Two implications follow:

- A duplicate or implementation-detail test can be deleted while the observed production behavior remains intact.
- A production behavior cannot be deleted merely because its test was classified as bloat.

Changing production behavior requires separate evidence from requirements, callers, specifications, history, or another independently justified target cluster. Adding characterization tests is not the default response to cleanup uncertainty.

## Verification independence

Verification adds value when the verifier has information, authority, or a failure domain meaningfully independent from the producer.

Preserve verification that defines content identity, checks an independently supplied digest, crosses a persistence boundary, detects corruption, authenticates an external publisher, or serves another independent consumer. Investigate locally generated checksums, receipts, manifests, envelopes, recomputation, and validators that can only reproduce the producer's assumptions and bugs.

Cryptographic vocabulary does not create independence. A strong hash can still be verification theater; a simple persisted readback can still be a meaningful boundary.

## Fallbacks and fail-visible behavior

Within trusted code, unexpected failures should normally remain visible. A broad catch-and-fallback path often converts an internal bug into plausible but incorrect output.

Preserve a fallback when it implements a documented missing-field rule, supported legacy version, external failure translation, cleanup obligation, or concrete recovery contract. Investigate it when it catches unrelated exceptions, guesses a replacement value, or survives only because a test was created for it.

The decision is about the failure contract, not the syntax of `try`/`except`.

## Scientific and numerical false positives

Numerical checks, tolerances, conservation laws, solver invariants, convergence criteria, physical bounds, resource limits, and independently derived reference results can look defensive while protecting real scientific meaning.

Preserve them when their mathematical or experimental purpose is concrete. Investigate duplicate kernels, copied formulas, self-comparisons, metadata receipts, or generic validation layers that detect no independent numerical failure class.

## Confidence and explicit preservation

- **HIGH:** the evidence chain is resolved and shows redundancy, unreachability, tautology, mutual support, or disconnection from a current contract.
- **MEDIUM:** the construct appears unnecessary, but caller, history, compatibility, or boundary evidence is missing.
- **LOW / preserve by default:** security, persistence, transactions, concurrency, external protocols, supported compatibility, resource limits, and scientific invariants whose purpose may not be locally visible.

Apply mode removes resolved HIGH candidates. It does not turn MEDIUM uncertainty into permission. A preservation decision is a successful outcome when the evidence does not support deletion.

## Subtraction without redesign

New dependencies, abstractions, wrappers, compatibility layers, provenance machinery, and replacement tests have a default budget of zero. New code is justified only when it preserves a real behavior while enabling a larger, focused subtraction.

If cleanup adds substantial structure or changes architecture, stop and re-establish the boundary.

Small corrective additions remain possible when they close a demonstrated protection gap, such as one current-path integration test or a direct required-input check. Their independent root and narrow scope must be explicit.

## Related approaches

Projects with adjacent goals include [code-humanizer](https://github.com/LeonardNJU/code-humanizer), [agent-sh/deslop](https://github.com/agent-sh/deslop), [dabit3/deslop](https://github.com/dabit3/deslop), and [ai-slop-cleaner](https://github.com/Yeachan-Heo/oh-my-claudecode/tree/main/skills/ai-slop-cleaner). `deslop` is intentionally narrower: accumulated test, verification, and fallback clusters with explicit preservation evidence.
