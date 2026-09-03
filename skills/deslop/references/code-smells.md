# Code Smells

Use this checklist for production code after test bloat and verification clusters have been inspected. A smell identifies where to investigate; caller, correction, and contract evidence decide whether to delete. Generic dead code and ordinary duplication are secondary unless they belong to a focused cluster.

| Smell | Signal | Evidence needed | Common false positives | Preferred simplification |
| --- | --- | --- | --- | --- |
| Repeated validation | `None`, type, enum, shape, or schema checks repeat after parsing | Trace the true input boundary and all direct callers | Independently callable API, mutation, persisted reload, distinct invariant | Validate once at the boundary |
| Phantom exception handling | Broad catches, catch/log/rethrow, impossible caught exception | Enumerate exceptions the operation can raise and required recovery | Cleanup, stable exception translation, documented retry policy | Remove the handler or narrow it to real recovery |
| Fallback proliferation | Default, legacy, and “safe” paths for states callers cannot produce | Trace configuration, supported environments, and selection paths | Availability requirements, rollout, heterogeneous deployments | Keep the required path and expose invalid state normally |
| Pass-through wrapper | Function only forwards arguments or renames a readable call | Confirm it adds no policy, lifecycle, stable seam, or representation change | Public facade, transaction boundary, instrumentation | Call the underlying operation directly |
| Wrapper tower | Adapter-to-adapter or DTO-to-equivalent-DTO chains | Follow data end to end and identify actual boundaries | Protocol translation, generated API surface | Collapse the chain at the nearest real boundary |
| Single-use helper | One private caller and a short obvious body | Check dynamic registration and whether the name encodes domain knowledge | Callback, recursion, framework hook, meaningful algorithm | Inline and delete helper-only tests |
| One-implementation abstraction | Interface, factory, strategy, registry, provider, or service with one real implementation | Inspect construction sites and supported extension commitments | External plugins, platform variants, real test seam | Use the concrete behavior directly |
| Premature utility | Generic helper unifies similar syntax through flags or callbacks | Decide whether callers share domain knowledge or only appearance | One authoritative business or protocol rule | Keep obvious local operations local |
| Repeated canonicalization | Normalizers run throughout one trusted call graph | Identify first non-canonical input and the consumer requiring canonical form | Signing format, Unicode rule, cache key, equality identity | Canonicalize once at the representation boundary |
| “Safe” wrapper type | `Validated`, `Canonical`, `Trusted`, or `Safe` type without a trust transition | Locate the representation or authority change it models | Capability type, protocol state, validated external input | Pass the ordinary typed value internally |
| Redundant copy or freeze | Each layer copies or freezes values without a mutation path | Trace aliases, ownership, concurrency, and external mutation | Views, caches, concurrency, API isolation promise | Keep one clear ownership boundary |
| Duplicate implementation | Near-identical functions or adapters accumulated across patches | Compare semantics, callers, failure modes, and ownership | Similar code with independent domain evolution | Delete the obsolete copy or use the existing direct path |
| Dead branch or stale flag | No call sites, impossible branch, fixed flag, overwritten value | Check reflection, registration, exports, config, and supported variants | Framework hooks, serialized names, CLI entry points | Delete the branch and its plumbing |
| Test-created reachability | A test mutates a gate, injects a future config, or calls a post-gate helper directly | Find an active config, request, persisted value, or runtime selector that reaches it | Current platform variants or staged rollouts with an owned work package | Delete the unreachable branch and its dedicated test |
| Compatibility residue | Alias, shim, or historical fallback has no supported consumer | Check support policy, releases, public API, and history | Third-party consumers, rolling upgrades, stored data | Delete only with affirmative end-of-support evidence |
| Product-surface loop | Registry entry, CLI command, diagnostic module, config, and tests only reference one another | Exclude the same cluster and locate a real caller, operator workflow, or external protocol | A documented and currently used public command | Delete the full inactive entry path, not one wrapper |
| Implicit schema default | Dataclass or parser defaults a missing identity/path/count to a historical value | Check current producers and stored-data support commitments | Truly optional presentation or enrichment fields | Make current identity explicit and fail on omission |
| Stale current documentation | PLAN, STATUS, architecture, or workflow text still promises a removed fallback or lists a completed fix as pending | Compare current callers/configs with authoritative documents | Clearly labeled history, migration guidance, or future proposals | Update the current claim while preserving labeled history |
| Comment noise | Text narrates syntax, types, or generic intent | Ask whether it contributes information not present in clear code | External constraint, workaround, invariant, tradeoff | Delete restatement; preserve concise “why” |
| Type workaround drift | Cast chains, ignores, and runtime probes conflict with surrounding conventions | Confirm current type contract and toolchain behavior | Broken third-party stubs, version-gated API | Express the real type directly and remove stale workarounds |
| Inferred transformation | Date, filename, project ID, or incidental metadata silently selects a data transform | Find the authoritative caller choice and historical failure evidence | Versioned protocol fields with explicit semantics | Replace guessing with an explicit option and record it |

## Fail-visible bias

Inside trusted code, unexpected failures should normally surface. Robustness is not a license to hide programming errors. Investigate these patterns first:

- broad `except Exception` around ordinary internal work;
- catch-log-rethrow that adds no stable translation, cleanup, or attribution;
- catch-and-fallback after a new path raises unexpectedly;
- `try new behavior; otherwise run old behavior` without a supported version or protocol signal;
- silent defaults after malformed or missing internal state;
- compatibility branches with no reachable supported consumer;
- repeated validation after a trusted boundary or after a typed representation is established;
- defensive branches whose only evidence is tests created for those branches.

For each branch, ask:

1. What exact failure is recoverable?
2. Does the current user requirement or protocol require recovery, translation, cleanup, or compatibility?
3. Can ordinary runtime failure expose an internal bug more usefully?
4. Is the fallback's test an independent contract, or part of a closed justification loop?
5. What supported consumer would break if this branch disappeared?

If the answer is only “be robust,” “future-proof,” or “keep old tests green,” prefer direct failure. A bug fix should replace incorrect behavior, not preserve it behind a fallback. Preserve narrow exception handling when it performs concrete cleanup, translates a stable public error, enforces a documented legacy protocol, or protects a real resource/transaction boundary.

## Defensive clusters, not isolated lines

Do not delete only the most visible helper while leaving its mutually supporting tests, validators, wrappers, or fallback branches. Follow the justification chain outward. If production code, a test, and a receipt/validator each exist only to justify one another, treat them as one deletion candidate. A cluster is preserved only when its chain reaches an independent user requirement, external caller, protocol, security boundary, persistence/corruption boundary, or scientific invariant.

## Deletion Evidence

Prefer concrete evidence such as:

- no static, dynamic, exported, or registered consumer;
- impossible state under the established typed contract;
- value already validated at the actual boundary;
- caught exception cannot originate in the protected operation;
- wrapper adds no observable behavior;
- fallback masks a programming or configuration error;
- duplicate path has an identified authoritative replacement;
- compatibility promise has explicitly ended;
- value is overwritten before observation.

Do not cite AI authorship as evidence.

## Abstraction Check

Before keeping an abstraction, ask what independent variation it contains today. “Could support another implementation later” is not enough. Before deleting one, check for external implementations, framework discovery, package commitments, platform variants, and tests that model a real seam rather than merely mock internals.

Do not replace removed abstraction with a differently named abstraction. A few duplicated obvious lines can be clearer than a shared layer that forces navigation across files.

A thin wrapper can still own a real boundary. Preserve one that bridges independently versioned formats, manages a temporary dataset or resource lifecycle, maintains a published import path, or translates a stable external contract. Thinness alone is not deletion evidence.

For active-config reachability and cross-layer ownership, also read [evidence-and-reachability.md](evidence-and-reachability.md).
