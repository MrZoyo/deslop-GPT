# Human adjudication

This reference-only record summarizes the actual reviewed field-trial outcome. It must not be exposed to an agent evaluated against the frozen `input/` snapshot.

## Initial read-only audit and first review

The original `$deslop deep` read-only audit identified five HIGH groups:

1. a parser-side missing-`VENDOR` → NVIDIA compatibility fallback;
2. duplicate retired-host ranking filtering and reaggregation;
3. broad collector exception containment that hid internal programming errors;
4. DB write failure being logged and ignored, creating false-health risk;
5. two unreachable or speculative fallbacks:
   - ranking topology `_other`;
   - static-demo `gpu_id`/`id` compatibility.

All five HIGH groups were manually reviewed and accepted for cleanup. The first reviewed cleanup was commit `22fb141f7bba3a561b03d9372700f7bffc1e0530` (`refactor: remove redundant collector fallbacks`).

The review explicitly preserved:

- remote NVIDIA/AMD vendor autodetection;
- malformed remote data remaining a per-host failure;
- expected SSH failure handling;
- tolerant AMD/ROCm parsing;
- persistence, security, and provenance boundaries.

## Deferred MEDIUM review

The initial review deferred four MEDIUM findings:

A. `/api/meta` initialization failure was silently swallowed;
B. an unknown badge reference was silently skipped after configuration validation;
C. the application could start without the bundled `web/` directory;
D. frontend security tests used source-shape regex assertions.

The second evidence review concluded:

- **A — changed:** initialization failure is now exposed to the user and stops startup initialization.
- **B — changed:** an unknown post-validation badge reference now exposes the broken invariant.
- **C — preserved:** packaging, API-only use, and import contracts were ambiguous.
- **D — preserved:** a proper behavioral replacement required substantial new fake-DOM and test infrastructure.

C and D were explicit preservation decisions after evidence review, not missed cleanup. The second reviewed cleanup was commit `76760d565fbd816c4a0f5bc3419fef159dbb7d7a` (`refactor: expose broken runtime invariants`).

No new Skill rule was justified by this single field trial. The private repository, production environment, hostnames, credentials, and private configuration are outside this record.
