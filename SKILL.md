---
name: deslop
description: Audit or apply deletion-first cleanup for defensive overengineering, test bloat, and circular verification while preserving externally meaningful behavior. Invoke explicitly for semantic simplification, not generic rewriting or redesign.
---

# Deslop

Remove unjustified complexity without changing intended externally observable behavior. This is not a beautification pass, generic rewrite, style migration, or architectural redesign.

Focus on three primary targets:

1. defensive bloat inside trusted code paths;
2. tests that add volume without distinct behavioral signal;
3. circular verification where the verifier has no meaningfully independent information, authority, or failure domain.

Dead code, wrapper towers, speculative abstractions, compatibility residue, and comment noise are secondary targets when evidence supports deletion.

## Modes and Authorization

Interpret the invocation from natural language; do not depend on a runtime-specific arguments variable.

- **Default or `audit`:** Read-only. Inspect and report candidates, evidence, confidence, and important constructs that should be preserved.
- **`apply`:** Modify files within the established scope.
- **`tests`:** Prioritize test-suite signal and delete or consolidate test bloat. Without `apply`, remain read-only.
- **`deep`:** Inspect repository-wide. Without `apply`, remain read-only; with `apply`, repository-wide cleanup is allowed but redesign is not.
- **Explicit paths:** Restrict inspection and edits to those paths plus the minimum callers, contracts, and tests required to understand them.
- **`current branch` or no scope inside Git:** Use current branch work relative to the actual local merge base and default or upstream base. Include relevant staged, unstaged, and untracked work; never assume `main`.

Only `apply` authorizes edits. Never infer edit authorization from phrases such as “clean this up” when the user invoked `$deslop` without `apply`.

Do not fetch, reset, switch branches, stage, commit, push, or create backups unless explicitly requested.

## 1. Establish the Boundary

Before editing:

1. Read applicable `AGENTS.md` files and repository conventions.
2. Inspect the requested scope, worktree state, relevant history, and documented verification commands.
3. Determine the local merge base when branch scope matters.
4. Read enough callers and tests to identify real contracts and ownership.
5. Preserve unrelated user changes.

If scope cannot be inferred safely, ask for it before applying changes.

## 2. Establish Behavior to Preserve

Use evidence in this order:

1. explicit user requirements;
2. public API behavior;
3. specifications and protocols;
4. existing meaningful tests;
5. real call sites;
6. documented invariants.

Do not preserve every internal accident. Do not add characterization tests merely to freeze current implementation details.

## 3. Classify Candidates

A pattern match is a lead, not a verdict. Confidence measures evidence, not ugliness.

- **HIGH:** Useless, duplicated, unreachable, tautological, pass-through, immediately overwritten, or disconnected from a real contract.
- **MEDIUM:** Apparently unnecessary, but caller, history, compatibility, or boundary context must be resolved first.
- **LOW / PRESERVE BY DEFAULT:** Security, authorization, concurrency, persistence, transactions, external protocols, resource limits, supported compatibility, and numerical invariants whose purpose may not be locally visible.

In apply mode:

- **HIGH:** Delete or simplify once the local impact and evidence are resolved.
- **MEDIUM:** Do not modify until the missing caller, contract, history, compatibility, or boundary question is resolved.
- **LOW:** Preserve unless direct contrary evidence is established.

Apply authorization is permission to edit, not permission to resolve uncertainty in favor of deletion.

Read references only when relevant:

- [references/code-smells.md](references/code-smells.md) for defensive code, wrappers, abstractions, dead paths, and comments.
- [references/test-smells.md](references/test-smells.md) whenever tests are in scope or support machinery being removed.
- [references/verification-and-trust.md](references/verification-and-trust.md) for validation, trust boundaries, provenance, checksums, signatures, schemas, or recomputation.
- [references/scientific-code.md](references/scientific-code.md) for scientific, numerical, simulation, ML, or engineering code.

## 4. Demand a Concrete Reason

For each non-trivial defensive or verification construct, answer:

1. What concrete failure does it prevent or detect?
2. Is that failure reachable from actual callers?
3. Is handling required by a contract or specification?
4. Does trust, authority, persistence, ownership, or failure domain change here?
5. Would ordinary parsing, typing, or runtime failure already be adequate?
6. Does the verifier know something meaningfully independent from the producer?

If no concrete answer exists, strongly prefer deletion. “Safer,” “more robust,” “future-proof,” and “might be useful” are not sufficient evidence.

## 5. Apply a Negative-Change Budget

A deslop pass should normally reduce code size and structural surface area.

| Addition during cleanup | Expected budget |
| --- | ---: |
| New dependencies | 0 |
| New abstractions or extension points | 0 |
| New compatibility layers | 0 |
| New cryptographic or provenance machinery | 0 |
| New wrappers or generic validators | 0 |
| New tests | Exceptional and minimal |

Treat every new helper, branch, validation layer, wrapper, fixture, and test as a cost requiring a concrete behavior-preservation reason. Adding code is acceptable only when necessary to preserve an existing meaningful behavior while removing more unnecessary machinery.

If an apply pass produces substantial positive net lines, more indirection, or more test surface, stop and reconsider before continuing.

## 6. Delete or Simplify

- Prefer direct local code over scaffolding.
- Validate once at a genuine boundary, then use a typed internal representation directly.
- Delete speculative error handling and allow the repository's ordinary failure mode when it is already adequate.
- Remove tests with no distinct behavioral signal; consolidate only when the result is clearer.
- Do not replace a deleted abstraction with another abstraction.
- Preserve small obvious duplication when a shared abstraction would encode no shared knowledge.
- Remove comments that restate code; preserve concise explanations of external constraints, surprising invariants, scientific assumptions, security boundaries, and real tradeoffs.
- In `deep apply`, exclude generated code, vendored dependencies, `third_party` trees, migration history, lockfiles, and externally generated snapshots or artifacts unless the user explicitly includes them or repository evidence establishes direct ownership.

Verification adds value only when the verifier has information, authority, or a failure domain meaningfully independent from the producer. Otherwise investigate the entire self-verification chain for deletion, including tests that exist only to protect it.

## 7. Verify Proportionally

1. Run the narrowest existing relevant tests or checks.
2. Group related HIGH-confidence deletions.
3. Re-run targeted checks after meaningful semantic groups, not every tiny edit.
4. Run the repository's documented final verification once when feasible.

Use existing verification commands. Do not create proof files, audit ledgers, checksum reports, or a new verification framework. If verification cannot run, state that plainly.

## Final Report

Keep the report compact and evidence-dense:

- scope inspected;
- **Removed:** major deletion categories and concrete evidence;
- **Preserved:** suspicious-looking constructs deliberately retained and why;
- tests removed or consolidated;
- checks actually run and their results;
- approximate net line change when easy to obtain;
- uncertainty intentionally left untouched.

Reporting preserved constructs is required: it demonstrates semantic judgment and exposes false-positive risk.
