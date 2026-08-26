# Design

`deslop` is a semantic cleanup policy for complexity accumulated through repeated coding-agent implementation and correction cycles. The frozen runtime [`SKILL.md`](../skill/deslop/SKILL.md) is authoritative; this document explains the model without duplicating every runtime instruction.

## Deletion-first, not deletion-maximal

The objective is the smallest focused subtraction that removes unjustified machinery while preserving externally meaningful behavior. Line deletion, test count, assertion count, and coverage percentage are not goals by themselves.

The three primary target clusters are:

1. accumulated test-suite bloat;
2. verification theater;
3. defensive and fallback bloat.

Generic formatting, broad refactoring, framework migration, architectural redesign, and style humanization are outside this purpose.

> **Reduce test surface, not behavior surface.**

## Independent evidence roots

A construct is justified when its dependency chain reaches evidence independent from the construct itself. Useful roots include:

- a current user requirement or correction;
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

## Related approaches

Projects with adjacent goals include [code-humanizer](https://github.com/LeonardNJU/code-humanizer), [agent-sh/deslop](https://github.com/agent-sh/deslop), [dabit3/deslop](https://github.com/dabit3/deslop), and [ai-slop-cleaner](https://github.com/Yeachan-Heo/oh-my-claudecode/tree/main/skills/ai-slop-cleaner). `deslop` is intentionally narrower: accumulated test, verification, and fallback clusters with explicit preservation evidence.
