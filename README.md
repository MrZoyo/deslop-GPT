# deslop

**A deletion-first Agent Skill for removing defensive overengineering, test bloat, and verification theater from agent-maintained codebases.**

`deslop` is a semantic cleanup policy, not a generic code humanizer. It asks what concrete contract or failure a construct serves, deletes machinery with no defensible answer, and explicitly records suspicious-looking code it chose to preserve.

Its three primary targets are:

```text
Defensive bloat
Test bloat
Verification theater
```

Dead code, wrapper towers, speculative abstractions, compatibility residue, and low-information comments are secondary targets.

## Why this exists

Deletion-oriented agents often fail in opposite directions:

- they preserve obvious bloat because deletion feels risky;
- they match a smell mechanically and remove a real boundary or invariant;
- they delete production code, then add more tests and scaffolding than they removed;
- they treat locally generated hashes, schemas, receipts, and evidence as meaningful verification.

`deslop` is designed around false-positive resistance. A verifier is useful only when it has information, authority, or a failure domain meaningfully independent from the producer. A test is useful only when it protects distinct behavior with a meaningful oracle.

## Safety model

The public Skill is conservative about starting and aggressive about subtracting once authorized:

| Invocation | Behavior |
| --- | --- |
| `$deslop` | Read-only audit |
| `$deslop audit` | Read-only audit |
| `$deslop apply` | Apply a scoped cleanup |
| `$deslop tests apply` | Focus on test-suite signal |
| `$deslop current branch apply` | Clean the branch relative to its actual merge base |
| `$deslop deep` | Repository-wide audit |
| `$deslop deep apply` | Repository-wide cleanup without redesign |

Implicit invocation is disabled in [`agents/openai.yaml`](agents/openai.yaml). The Skill never interprets an ordinary request as permission for destructive cleanup.

## Install

Codex loads user-level skills from `$HOME/.agents/skills`. Install this repository directly:

```bash
git clone https://github.com/MrZoyo/deslop-GPT.git "$HOME/.agents/skills/deslop"
```

Update it later with:

```bash
git -C "$HOME/.agents/skills/deslop" pull --ff-only
```

You can also invoke `$skill-installer` in Codex and ask it to install the skill from this repository URL. Codex detects skill changes automatically; restart Codex if it does not appear.

## What makes it different

This project does not claim to be the first AI-code cleaner. Its narrower focus is:

1. redundant defensive programming inside trusted paths;
2. test suites as first-class cleanup targets;
3. circular verification beyond SHA, including schema, recomputation, evidence, signatures, and receipts;
4. scientific and numerical false-positive avoidance;
5. a production-derived adversarial corpus pairing every deletion target with a preservation case;
6. behavior preservation as the first evaluation metric.

Related projects include:

- [LeonardNJU/code-humanizer](https://github.com/LeonardNJU/code-humanizer)
- [agent-sh/deslop](https://github.com/agent-sh/deslop)
- [dabit3/deslop](https://github.com/dabit3/deslop)

Evaluation tools that influenced this repository:

- [tardigrde/agent-skill-eval](https://github.com/tardigrde/agent-skill-eval)
- [TiesPetersen/SkillBenchmark](https://github.com/TiesPetersen/SkillBenchmark)

No superiority claim is made without comparable repeated runs.

## Evaluation corpus

The repository includes 20 de-identified Python fixtures derived from accepted changes and active contracts in two robotics data pipelines, plus one authorization case:

| Class | Cases | Purpose |
| --- | ---: | --- |
| Confirmed boundary | 10 | Detect false-positive deletion |
| Confirmed change | 10 | Measure simplification recall |
| Authorization control | 1 | Confirm default invocation stays read-only |
| Baseline contract tests | 37 | Confirm every fixture starts valid |
| Grader calibration states | 40 | Prove every oracle accepts a valid state and rejects an invalid state |

The pairs cover dead helpers versus public façades, redundant tests versus atomic publication, duplicated option definitions versus real format orchestration, contradictory recovery flags versus precise compatibility fallback, inferred transforms versus external geometry gates, forced defaults versus data-quality constraints, duplicate sanitizers versus credential redaction, fixture-tautological tests versus physical outcome rules, duplicated payloads versus frozen ledgers, and batch-wide identity paranoia versus persisted media validation.

Case IDs and prompts are deliberately neutral. Ground-truth labels live in [`evals/adjudication.json`](evals/adjudication.json), which is not copied into the agent workspace. [`evals/grade_case.py`](evals/grade_case.py) applies hidden AST checks, independent behavior calls, fault injection, persistence corruption, authorization checks, and a recursive negative-change budget after the agent finishes. Each simplify case has a `golden_after` calibration overlay; each preserve case has a `destructive_mutant` overlay.

Results are intentionally not published yet. Model scores will be added only after repeated, pinned, reproducible A/B runs. Fixture count and passing pre-cleanup tests are not evidence of Skill effectiveness.

See [`evals/README.md`](evals/README.md) for the protocol and metrics.

## Validate locally

The dependency-free validator checks Skill structure, explicit-only policy, neutral prompts, corpus/adjudication agreement, confirmed evidence classes, the manifest-declared 20 fixtures and 37 baseline tests, bidirectional hidden-grader calibration, recursive negative-change enforcement, canonical Skill discovery metadata, and authorization safety:

```bash
python3 scripts/validate_corpus.py
```

`agent-skill-eval 0.7.0` installs Codex skills into the legacy `.codex/skills` path. All Codex benchmark commands therefore go through the pinned compatibility wrapper, which switches only Codex to the [current canonical `.agents/skills` path](https://developers.openai.com/codex/skills). Validate the harness format through `uv`:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/evals.json
```

Run a real Codex A/B evaluation with a deliberately pinned model and repeated trials:

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
  --post-grade-command "python3 evals/grade_case.py"
```

Before any `run`, the wrapper binds the installation name to the suite/frontmatter name `deslop` even when the checkout directory is named `deslop-GPT`, refuses ambient canonical, legacy, or admin `deslop` Skill paths that could contaminate the without-Skill baseline, then installs the evaluated Skill into a temporary `.agents/skills/deslop` directory and verifies the installed content hash. Run benchmarks from a clean user profile or container; the wrapper never moves user files. The required post-grade hook repeats the path/hash check in every with-Skill Codex workspace and records it under `skill_discovery` in `run_meta.json`. A run that bypasses the wrapper or hook must not be published as a benchmark result.

Record the model, reasoning effort, Codex version, harness version, run count, token cost, and wall time with every published result.

## Evaluation priorities

Metrics are ordered deliberately:

1. **Behavior Preservation Rate** — proportion of `confirmed_boundary` cases that pass hidden contracts.
2. **Slop Removal Recall** — proportion of `confirmed_change` cases that reach the adjudicated simpler state and pass hidden contracts.
3. **Complexity Reduction** — net lines, wrappers, validators, branches, and test cases removed.
4. **Cleanup-induced Slop** — production lines, test lines, helpers, abstractions, validations, and dependencies added by cleanup.

A large deletion with a low preservation rate is failure. A cleanup that grows the codebase with new scaffolding is also failure.

## Repository layout

```text
SKILL.md                         Core workflow and authorization model
agents/openai.yaml               UI metadata and explicit-only policy
references/code-smells.md        Defensive and structural checklist
references/test-smells.md        Test pruning and oracle independence
references/verification-and-trust.md
                                 Trust decision tree and circular verification
references/scientific-code.md    Numerical false-positive guidance
evals/evals.json                 agent-skill-eval suite
evals/adjudication.json          Labels, evidence class, and oracle source
evals/calibration/               Positive goldens and destructive mutants
evals/grade_case.py              Hidden post-grade contracts and budget checks
evals/files/                     Neutral paired fixtures copied to agents
scripts/validate_corpus.py       Dependency-free static validation
scripts/run_agent_skill_eval.py  Pinned canonical-path compatibility wrapper
```

Fixtures live under `evals/files/` rather than a top-level `fixtures/` directory because that is the native safe-path layout consumed by `agent-skill-eval`.

## Contributing

The most valuable contribution is a small paired case with adjudicated evidence:

- one fixture where a construct should be removed;
- one nearby counterexample where it must be preserved;
- an independent behavioral oracle;
- deterministic assertions that expose both over-preservation and over-deletion.

Current-project smells without historical or contract evidence belong in an audit candidate pool, not the scored corpus. Avoid adding a rule without a false-positive case.

## License

[MIT](LICENSE)
