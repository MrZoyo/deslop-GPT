# Evaluation protocol

This public `dev-v1` suite measures semantic cleanup rather than keyword deletion. It contains 10 paired `confirmed_change` and `confirmed_boundary` cases plus one default-audit authorization control. Because these cases informed Skill and grader design, they are development data rather than a held-out basis for public performance claims.

The fixtures are clean-room, de-identified reductions of patterns found in Praxis and an MCAP preprocessing pipeline. They preserve relationships and failure modes, not proprietary code, paths, data, constants, schemas, or artifact identities.

## Bootstrap rule

The Skill must not provide its own ground truth. Evidence is classified before a case enters the scored corpus:

- **Confirmed change:** a simplification already accepted in project history with behavior tests or equivalent evidence.
- **Confirmed boundary:** an active external, persistence, security, protocol, scientific, or compatibility contract supported by code and tests.
- **Audit candidate:** a current smell without independent adjudication. Candidates are not scored and must not be promoted merely because `$deslop audit` reported them.

This avoids the circular workflow “the Skill says this is slop, therefore the fixture proves the Skill detects slop.”

## Corpus map

| Pair | Confirmed change | Confirmed boundary |
| ---: | --- | --- |
| 1 | Uncalled parser and digest helpers | Published façade used by an external caller |
| 2 | Aggregate assertion duplicated by stronger item checks | Atomic publication cleanup and exception propagation |
| 3 | Duplicate option definitions across two parsers | Wrapper joining two independently versioned formats |
| 4 | Contradictory continue/fail-fast controls | Exact fallback for a documented legacy field |
| 5 | Timestamp-derived image transformation | Explicit format and calibrated geometry gates |
| 6 | Adapter re-locks a caller-configurable value to its default | Format consistency and source-frame gap limits |
| 7 | Adapter duplicates a shared metadata sanitizer | Credential redaction and non-secret config fingerprint |
| 8 | Test asserts only its own empty temporary fixture | Physical event order, numerical validity, and rebound limits |
| 9 | Full episode payload duplicated for every sample | Frozen persisted ledger and manifest identity |
| 10 | Batch rejects multiple independently embedded calibrations | Media readback across write/persistence boundary |

`mode-default-audit` reuses case `c01a` and requires the meaningful workspace file set and every supplied byte to remain unchanged. Its first-class side-effect contract also rejects branch, commit, review-request, and worktree-state changes.

## Preventing answer leakage

- Workspace directories and eval IDs are neutral (`c01a`, `c01b`, ...).
- Prompts never say which construct to delete or preserve and do not mention `$deslop` themselves.
- `force_skill_invocation` adds `$deslop` only to the with-Skill configuration, so the without-Skill baseline receives the same natural cleanup task without an unknown Skill name.
- Visible tests establish ordinary caller context but are not the benchmark oracle.
- Labels and oracle provenance live in `adjudication.json`, outside the files copied to the agent.
- `grade_case.py` runs after grading while the workspace still exists.
- The external grader uses AST checks, independent calls, fault injection, persistence tampering, remaining-test execution, and exact audit workspace comparison.
- A second hook assertion recursively compares relative file paths and Python lines, rejects new files or substantial growth, and records AST structural deltas.
- Successful Skill discovery is metadata only; it emits a scored assertion only when path or content-hash verification fails.

The grader is public for reviewability, but it is not installed into the evaluated workspace. A network-capable agent could deliberately inspect this repository; benchmark runs should prohibit unrelated network access and retain tool logs.

## Metric order

1. **Behavior Preservation Rate**

   ```text
   passing confirmed_boundary cases / 10
   ```

   False-positive deletion rate is `1 - Behavior Preservation Rate`. This is the primary KPI.

2. **Slop Removal Recall**

   ```text
   passing confirmed_change cases / 10
   ```

3. **Hidden Contract and Remaining-Test Pass Rate**

   Every semantic case must pass its independent post-grade contract and all remaining `unittest` tests. Visible tests alone do not establish correctness, but a cleanup may not leave the remaining suite broken.

4. **Complexity Reduction**

   Compare nonblank lines, functions, test functions, classes, branches, exception machinery, assertion sites, runtime type checks, imports, and adjudicated duplicated payloads. Line deletion alone is not a quality score.

5. **Cleanup-induced Slop**

   Record new files, production/test nonblank lines, functions, test functions, classes, branches, exception machinery, Python assert statements, unittest assertion calls, runtime type checks, imports, and likely abstractions. The hook enforces a small recursive file/line budget and reports AST deltas without turning every structural metric into a hard failure.

6. **Authorization Safety**

   `mode-default-audit` must leave the meaningful workspace file set and supplied bytes unchanged, create no Git or review side effects, and pass the harness side-effect contract.

## Validate fixtures

Run the dependency-free validator:

```bash
python3 scripts/validate_corpus.py
```

It validates:

- the Skill and explicit-only policy;
- neutral IDs and prompts;
- fixture/adjudication agreement;
- confirmed evidence classes only;
- the manifest-declared 20 fixture directories and 37 pre-cleanup tests;
- bidirectional hidden-grader calibration: 20/20 valid states pass and 20/20 invalid states fail, with every simplify golden also passing its remaining visible tests;
- alternate-valid calibration for differently named tests, retained non-semantic provenance, and a different delegation shape;
- remaining-test rejection for both a failing suite and a zero-test workspace;
- recursive negative-change rejection for a nested-package mutant;
- score-neutral successful Skill discovery plus a hard failure for path/hash mismatch;
- canonical `.agents/skills/deslop` path, installed content hash, and `run_meta.json` evidence;
- zero-mutation audit rejection for added, modified, and deleted files.

`agent-skill-eval 0.7.0` still targets Codex's legacy `.codex/skills` directory, derives the installed Skill name from the checkout directory, and compares worktree side effects against the full post-state. Use the repository wrapper for every harness command; it patches the pinned process to `.agents/skills`, binds the install name to the suite/frontmatter name, compares worktree status pre/post, refuses ambient canonical, legacy, or admin `deslop` Skill paths that would contaminate the baseline, and runs a path/content-hash smoke test before evaluation. Run the benchmark from a clean user profile or container, then validate the manifest:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill . \
  --evals evals/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/evals.json
```

The harness may warn that the suite has no visible assertions or natural-trigger case. Both are intentional: semantic assertions come from the post-grade hook, and `deslop` is explicit-invocation only.

## Run Codex A/B

Pin every reproducibility variable and include the required post-grade hook:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill . \
  --evals evals/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 5 \
  --baseline \
  --post-grade-command "python3 evals/grade_case.py" \
  --workspace eval-workspace/deslop
```

A result produced without the wrapper or `--post-grade-command "python3 evals/grade_case.py"` has no trustworthy Codex Skill discovery evidence or semantic adjudication and must not be reported as a project score. Each with-Skill Codex `run_meta.json` must contain verified `skill_discovery` path and content-hash metadata.

Use a targeted pair while iterating:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill . \
  --evals evals/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 3 \
  --baseline \
  --eval-id c01a \
  --eval-id c01b \
  --post-grade-command "python3 evals/grade_case.py"
```

Generate the harness report:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py report \
  --workspace eval-workspace/deslop \
  --format markdown \
  --show-evidence
```

Split preservation and simplification results using `evals/adjudication.json`; do not publish only the harness-wide aggregate.

## Reporting rules

Publish no result without:

- Skill commit SHA;
- model and reasoning effort;
- Codex and harness versions;
- run count and raw per-run outcomes or a confidence interval;
- baseline and with-Skill results;
- separate preservation and simplification rates;
- authorization-control result;
- token cost and wall time;
- negative-change evidence;
- failed cases, not only aggregate success.

`dev-v1` results are for iteration and diagnostics. Public model-effect claims additionally require a held-out corpus frozen after the evaluated Skill version; development and holdout results must be reported separately.

Competitor comparisons require the same fixtures, neutral prompts, models, reasoning settings, run counts, workspace permissions, hidden grader, and invocation adapter. Do not label one project better from unmatched runs.

## Adding a pair

1. Obtain historical-change evidence or an independently documented boundary.
2. Create the smallest de-identified `cNN[a|b]` fixtures.
3. Keep labels and expected action out of workspace files and prompts.
4. Add an independent contract to `grade_case.py`.
5. Record evidence class and oracle source in `adjudication.json`.
6. Add a `golden_after` overlay for a change or a `destructive_mutant` overlay for a boundary.
7. Add an `alternate_valid` overlay when the oracle risks binding to one historical implementation shape.
8. Verify both polarities and all alternate valid states with `scripts/validate_corpus.py`.

Current-project smells without independent adjudication belong in an audit backlog, not this manifest.
