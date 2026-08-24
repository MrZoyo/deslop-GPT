# Scientific and Numerical Code

Generic software robustness is not numerical correctness. In scientific, simulation, ML, and engineering code, preserve checks with a mathematical, physical, resource, or data-boundary reason; investigate enterprise-style hardening that has none.

## Decision Criteria

```text
Does the check enforce a documented mathematical, physical, convergence,
conditioning, tolerance, allocation, or external-data requirement?
|
+-- Yes -> preserve it and keep the reason visible
|
`-- No
    `-- Does it detect a concrete independent failure or trust transition?
        +-- Yes -> preserve if the check can actually detect that failure
        `-- No  -> likely generic hardening; simplify or delete
```

Prefer the ordinary path:

```text
typed caller input
    -> direct readable numerical kernel
    -> plain result
```

## Investigate Aggressively

- cryptographic identity or tamper receipts for in-memory arrays;
- `ResultEnvelope`, `VerifiedArray`, or canonical-array wrappers with no boundary;
- finite-real and positive-real validation repeated at every layer;
- generic stable-product, stable-ratio, or “safe arithmetic” frameworks added speculatively;
- arbitrary overflow or underflow guards disconnected from the project's numerical model;
- output-finiteness checks repeated after the responsible kernel already establishes the invariant;
- defensive copies of every returned array without aliasing risk;
- duplicate recomputation described as verification;
- schema, provenance, or evidence files produced and consumed within one experiment process;
- runtime type checks that restate typed internal APIs.

Use ordinary floating-point computation when that is the project's intended model. Do not impose exact arithmetic, universal finiteness, or cryptographic integrity merely because they sound safer.

## Preserve When Scientifically Meaningful

- solver convergence and termination criteria;
- physical domain constraints;
- covariance symmetry or positive-semidefiniteness when mathematically required;
- conditioning checks tied to algorithm validity;
- documented numerical tolerances and error budgets;
- known limiting cases and conservation laws;
- required event or phase ordering when final state alone can hide an invalid trajectory;
- explicit failure categories that preserve experiment denominators and diagnostic attribution;
- finite-result checks where downstream mathematics specifically requires finiteness;
- bounded allocation and resource constraints;
- checks preventing invalid numerical algorithms;
- validation of external datasets, models, checkpoints, and instrument files;
- provenance consumed independently for reproducibility or audit.

## Copies and Mutability

Before deleting a copy, trace array ownership, views, aliases, mutation sites, caches, concurrency, and library calls that may mutate inputs. A new array is not automatically untrusted; a view into shared mutable storage can still require isolation.

Before preserving immutability machinery, identify the reachable mutation that it prevents. “Results should be safe” is not enough.

## Numerical Verification

An analytical result, conservation law, independently derived implementation, calibrated reference dataset, or known limiting behavior can provide a real oracle. Repeating the same kernel with the same formula and inputs usually cannot.

Do not remove a numerical check merely because it resembles ordinary defensive validation. State its mathematical purpose first; delete only when no such purpose or independent failure class exists.

Do not collapse several scientifically distinct failures into one “result looks acceptable” assertion. A final target can be reached after an invalid event order, numerical instability, collision, limit violation, or rebound. Preserve separate checks when those outcomes change acceptance, the experiment denominator, or root-cause analysis.
