# Verification and Trust

Verification adds value only when the verifier has information, authority, or a failure domain meaningfully independent from the producer. A checksum is not automatically a trust boundary, and a second function or test is not automatically an independent oracle.

## Closed justification loops

Trace the whole dependency cluster outward:

```text
production result
    -> digest / receipt / manifest / validator
    -> validator test
    -> reason each member exists
    -> independent evidence root?
```

Production code does not justify a test merely because the test exercises it. A test does not justify production code merely because the production code exists. If a checksum exists only because its test expects it, and that test exists only because the checksum was added, the pair is **mutual-support slop**. The same loop can contain serialization added only for hashing, digest fields, result envelopes, manifests, receipts, recomputation, wrappers, and wrapper-only tests.

Delete the whole closed cluster when its chain reaches no independent root. Independent roots include:

- a current user requirement or correction;
- a real external caller or public API contract;
- a documented wire protocol or specification;
- a separately controlled security key or trust authority;
- an independently supplied manifest, release digest, or content-addressed identity;
- a persistence/readback or corruption boundary;
- an independent consumer, regulator, reproducibility workflow, or operational system;
- a scientific or numerical invariant with an independently derived expected result.

Preserve one member only when the remaining cluster still serves such a root. Do not preserve every member because another member depends on it.

## Trust-boundary decision tree

```text
Does the value cross out of the current trusted execution domain?
|
+-- No
|   `-- Is there concrete corruption, persistence, ownership, concurrency,
|       or independent hardware/process failure to detect?
|       +-- No  -> verification is probably redundant
|       `-- Yes -> preserve only the check that can detect that failure
|
`-- Yes
    `-- Is the source independently controlled or untrusted?
        +-- Yes -> parse / validate / decode once at the boundary
        `-- No
            `-- Does a protocol, specification, or consumer require it?
                +-- Yes -> preserve the required check
                `-- No  -> identify the concrete failure model first
```

Public visibility alone does not create a trust boundary. Two services owned by the same producer can still be circular; one process can still cross a real failure domain by writing, publishing, reopening, decoding, or reading persisted output.

## Independence test

For every claimed verification, record:

1. **Producer:** who created the value?
2. **Verifier:** who checks it?
3. **Independent knowledge:** what does the verifier know that the producer did not generate?
4. **Independent authority:** is there a separate key, manifest, specification, identity, or consumer?
5. **Independent failure domain:** can producer and verifier fail differently?
6. **Action:** what meaningful response follows failure?

If all inputs, logic, authority, and failure modes are shared, the check is circular even when it uses cryptography or another process.

## SHA256 and checksum clusters

Treat SHA256/checksum machinery as a cluster, not as one function. Search for the entire chain:

```text
canonicalization / serialization added only for hashing
    -> digest field or checksum helper
    -> result envelope / manifest / receipt
    -> recomputation or validator
    -> tests and fixtures created only for those mechanisms
```

When there is no independent expected digest, identity authority, trust transition, persistence-corruption role, content-addressing role, or external consumer, investigate and remove the whole support chain. Strong deletion candidates include hashes of local arguments, parameter objects, internal arrays, result dataclasses, self-created manifests, self-issued receipts, and evidence consumed only by the same agent or process.

Do not call a local digest authentication merely because it is SHA256. A digest retained after secret redaction can be a legitimate non-secret correlation fingerprint when an independently recorded input or consumer uses it; that is provenance, not authentication, and its independent role must be explicit.

## Verification-theater patterns

### Recompute theater

```text
calculate result -> repeat the same calculation -> call it verified
```

Delete when both computations share algorithm, inputs, constants, and likely bugs. Preserve independently derived analytical checks, diversified implementations with a concrete safety purpose, and cheap invariants that detect a distinct failure class.

### Schema and envelope theater

```text
producer emits payload -> producer-owned schema mirrors payload -> producer validates it
```

Delete when no external protocol, persisted format, or independent consumer relies on the schema. Preserve wire contracts and independently maintained schemas.

### Receipt, manifest, and evidence theater

```text
operation -> evidence.json / receipt -> local validator -> local test
```

Delete ledgers and validators generated and consumed only by the same trusted workflow. Preserve records required by a separate authority, operational system, regulator, reproducibility workflow, transaction, idempotency boundary, or corruption detector.

### Signature theater

```text
generate local key -> sign local result -> verify with paired local key
```

Delete when no identity, key custody, distribution boundary, or independent trust anchor exists. Preserve signatures authenticating an external publisher, protocol peer, or independently controlled key.

## Persistence and readback

Reopening an encoded file, archive, media object, or persisted record can be genuinely independent when it detects truncation, partial publication, codec mismatch, schema loss, or corruption across a write/read boundary. Do not collapse that into circular in-memory recomputation. Conversely, reading a value back from the same memory representation without a distinct failure domain adds little.

## Defensive and fallback checks

Repeated null/type/shape checks, broad catches, catch-log-rethrow, catch-and-fallback, repeated normalization, and self-validating result objects are suspicious when they add no boundary or failure domain. Preserve checks that enforce a documented safety, resource, authorization, transaction, concurrency, persistence, protocol, or numerical invariant.

Prefer direct failure for unexpected internal errors. A narrow fallback for one documented missing field or supported legacy version is different from `except Exception: use_old_path()`. The former may be contractual while the compatibility window remains; the latter hides bugs unless independent evidence proves otherwise.

## Preserve by default

When evidence is incomplete, preserve security and authorization, real external protocols, supported compatibility, persistence and transactions, concurrency, resource limits, scientific invariants, independently supplied artifact verification, and content-addressed identity. Report the missing evidence instead of inventing a justification or deleting on aesthetic grounds.
