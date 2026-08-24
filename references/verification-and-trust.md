# Verification and Trust

Verification adds value only when the verifier has information, authority, or a failure domain meaningfully independent from the producer. Hashing is only one form of circular verification.

## Trust-Boundary Decision Tree

```text
Does the value originate outside the current trusted execution domain?
|
+-- No
|   `-- Is there a concrete corruption, concurrency, persistence, ownership,
|       or independent hardware/process failure being detected?
|       +-- No  -> validation or verification is likely redundant
|       `-- Yes -> preserve only if the check can detect that failure
|
`-- Yes
    `-- Is the source independently controlled or untrusted?
        +-- Yes -> parse and validate once at the boundary
        `-- No
            `-- Does an external protocol, specification, or consumer require it?
                +-- Yes -> preserve the required check
                `-- No  -> investigate the concrete failure model further
```

Public visibility alone does not create a trust boundary. An exported library function may accept hostile third-party input, but that requires contract or consumer evidence.

## Typical Boundaries

Usually genuine:

- user-controlled input;
- external network input;
- independently produced files, datasets, manifests, or artifacts;
- deserialization from bytes into structured values;
- service, process, machine, or organization boundaries when trust changes;
- signed or authenticated protocols;
- persistence read after independent mutation or corruption is possible;
- content-addressed systems where a digest is identity;
- provenance consumed by an independent system or authority.

Usually not genuine by themselves:

- one internal function calling another;
- a dataclass passed between local modules;
- an exported function used only by trusted project code;
- a new in-memory array;
- an internal result object;
- a helper returning another helper's result;
- two layers in the same typed process.

At a real boundary, prefer:

```text
untrusted input
    -> parse / validate / decode once
    -> typed internal representation
    -> direct computation
```

Do not propagate hostility inward through every function.

## Independence Test

For any claimed verification, identify:

1. **Producer:** Who created the value?
2. **Verifier:** Who checks it?
3. **Independent knowledge:** What does the verifier know that the producer did not generate?
4. **Independent authority:** Does the verifier trust a separate key, specification, manifest, or identity?
5. **Independent failure domain:** Can the producer and verifier fail differently?
6. **Action:** What meaningful response follows failure?

If producer and verifier share all inputs, logic, authority, and failure modes, the check is circular even when it uses cryptography.

Independence is semantic, not a process-count heuristic. Code in one process can cross a real failure domain by encoding, writing, atomically publishing, reopening, parsing, or decoding persisted output. A readback validator may detect truncation, partial publication, codec mismatch, schema loss, or corruption that an in-memory assertion cannot. Conversely, two services controlled by the same producer with the same inputs and algorithm may still be circular.

## Verification-Theater Taxonomy

### Hash Theater

```text
produce local value -> hash it -> store digest beside it -> recompute own digest
```

Delete when both value and expected digest come from the same trusted workflow. Preserve downloaded-artifact checks, external manifests, content-addressed identity, deduplication semantics, signed protocols, and independent corruption detection.

A digest retained while secret configuration text is redacted can be a legitimate non-secret fingerprint for correlating independently recorded inputs. Do not describe that fingerprint as authentication, but do not delete it merely because it is computed locally.

### Schema Theater

```text
producer emits payload -> producer-owned schema mirrors payload -> producer validates it
```

Delete when the schema expresses no independent protocol or consumer contract. Preserve schemas defined by an external API, wire protocol, persisted format, cross-team boundary, or independently maintained consumer.

### Recompute Theater

```text
calculate result -> wrapper repeats the same calculation -> call it verified
```

Delete when both computations share the same algorithm, inputs, constants, and likely bugs. Preserve independently derived analytical checks, diversified implementations with a concrete safety purpose, and cheap invariants that detect a distinct failure class.

Reopening Parquet, media, archives, or serialized records and checking their decoded representation is not the same as recomputing an in-memory result. Preserve it when the write/encode/read path introduces concrete failures and the readback check observes them.

### Evidence Theater

```text
operation -> evidence.json -> audit.json -> verification.json
```

Delete ledgers generated and consumed only by the same agent or process when no independent consumer, policy, or failure boundary exists. Preserve audit records required and consumed by a separate authority, operational system, regulator, or reproducibility workflow.

### Signature Theater

```text
generate local key -> sign local result -> verify locally with paired local key
```

Delete when no identity, key custody, distribution boundary, or independent trust anchor exists. Preserve signatures that authenticate an external identity, artifact publisher, protocol peer, or independently controlled key.

### Receipt and Capability Theater

```text
ordinary function call -> issue receipt/token/permit -> consume once locally
```

Delete when the token controls no real authority transition or replay risk. Preserve capabilities and receipts that cross a real privilege, transaction, idempotency, billing, or distributed-systems boundary.

## Defensive Programming

Investigate repeated null/type checks, broad catches, catch/log/rethrow, impossible exception branches, repeated normalization, defensive copies without aliasing risk, and result objects that revalidate themselves.

Preserve checks that:

- enforce a distinct invariant at the actual boundary;
- prevent a documented safety or resource hazard;
- translate external failure into a stable public contract;
- protect authorization, concurrency, transactions, or persistence semantics;
- detect a failure source independent from the producer.

Ordinary runtime failure is often adequate for internal programming errors.

Precise fallback can also be contractual: catching one missing-field or version signal and reading a documented legacy representation differs from broad catch-and-continue recovery. Preserve the former while the compatibility window remains supported.

## SHA and Checksums

Do not delete cryptography because it uses SHA256. Delete it when it pretends an ordinary in-process operation needs authentication.

Strong deletion candidates include hashes of local arguments, parameter objects, result dataclasses, internal arrays, locally created manifests, self-issued receipts, or evidence with no independent consumer.

Strong preservation candidates include independently supplied release digests, signed manifests, authenticated protocols, content-addressed storage, cache keys whose semantics require content identity, and persisted cross-system provenance.

## Preserve by Default

When evidence is incomplete, preserve authentication, authorization, security boundaries, concurrency correctness, persistence and transactions, external protocols, resource limits, and supported compatibility. Report uncertainty instead of guessing.
