# deslop

**A deletion-first Agent Skill for removing accumulated agent-created test bloat, verification theater, and defensive/fallback bloat from agent-maintained codebases.**

`deslop` is a semantic cleanup policy, not a generic code humanizer. It asks what concrete contract or failure a construct serves, deletes machinery with no defensible answer, and explicitly records suspicious-looking code it chose to preserve.

Its three primary targets, in priority order, are:

```text
Test-suite bloat (~50%)
Verification theater (~25%)
Defensive/fallback bloat (~25%)
```

Generic dead code, wrapper towers, speculative abstractions, compatibility residue, and low-information comments are secondary targets. They are in scope only when they belong to one of the three focused clusters.

## Why this exists

Deletion-oriented agents often fail in opposite directions:

- they preserve obvious bloat because deletion feels risky;
- they match a smell mechanically and remove a real boundary or invariant;
- they delete production code, then add more tests and scaffolding than they removed;
- they treat locally generated hashes, schemas, receipts, and evidence as meaningful verification.

`deslop` is designed around false-positive resistance and closed justification loops. A verifier is useful only when it has information, authority, or a failure domain meaningfully independent from the producer. A test is useful only when it protects distinct behavior with a meaningful oracle. Production code does not justify a test merely because the test exercises it, and a test does not justify production code merely because the production code exists.

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

Implicit invocation is disabled in [`skill/deslop/agents/openai.yaml`](skill/deslop/agents/openai.yaml). The Skill never interprets an ordinary request as permission for destructive cleanup.

## Install

The runtime Skill is the self-contained [`skill/deslop/`](skill/deslop/) directory. Ask `$skill-installer` to install this GitHub directory:

```text
https://github.com/MrZoyo/deslop-GPT/tree/main/skill/deslop
```

Current [OpenAI Skill documentation](https://developers.openai.com/codex/skills) uses `$HOME/.agents/skills` as the canonical user discovery path. The bundled `$skill-installer` may still copy into its legacy `$CODEX_HOME/skills` destination; use the symlink method below when the canonical path itself matters.

For local development, clone the repository outside the Skill discovery tree and symlink only the runtime directory. [OpenAI's Skill documentation](https://developers.openai.com/codex/build-skills) confirms that Codex follows symlinked Skill folders:

```bash
git clone https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skill/deslop" "$HOME/.agents/skills/deslop"
```

Update that checkout with `git -C "$HOME/.local/share/deslop-GPT" pull --ff-only`. Codex detects Skill changes automatically; restart Codex if an update does not appear.

## What makes it different

This project does not claim to be the first AI-code cleaner. Its narrower focus is:

1. accumulated test-suite bloat as the first cleanup target;
2. circular verification beyond SHA, including schema, recomputation, evidence, signatures, and receipts;
3. defensive and fallback accumulation that masks current errors;
4. scientific and numerical false-positive avoidance;
5. a production-derived adversarial corpus pairing every deletion target with a preservation case;
6. behavior preservation as the first evaluation metric.

Related projects include:

- [LeonardNJU/code-humanizer](https://github.com/LeonardNJU/code-humanizer)
- [agent-sh/deslop](https://github.com/agent-sh/deslop)
- [dabit3/deslop](https://github.com/dabit3/deslop)
- [oh-my-claudecode/ai-slop-cleaner](https://github.com/Yeachan-Heo/oh-my-claudecode/tree/main/skills/ai-slop-cleaner)

Evaluation tools that influenced this repository:

- [tardigrde/agent-skill-eval](https://github.com/tardigrde/agent-skill-eval)
- [TiesPetersen/SkillBenchmark](https://github.com/TiesPetersen/SkillBenchmark)

No superiority claim is made without comparable repeated runs.

## Development corpora

The public `dev-v1` corpus includes 20 de-identified Python fixtures derived from accepted changes and active contracts in two robotics data pipelines, plus one authorization case. These cases informed Skill and grader design; they are development data, not a held-out basis for public performance claims.

| Class | Cases | Purpose |
| --- | ---: | --- |
| Confirmed boundary | 10 | Detect false-positive deletion |
| Confirmed change | 10 | Measure simplification recall |
| Authorization control | 1 | Confirm default invocation stays read-only |
| Baseline contract tests | 37 | Confirm every fixture starts valid |
| Core grader calibration states | 40 | Prove every oracle accepts a valid state and rejects an invalid state |
| Alternate valid states | 3 | Reject historical-patch-only grading in representative cases |

The pairs cover dead helpers versus public façades, redundant tests versus atomic publication, duplicated option definitions versus real format orchestration, contradictory recovery flags versus precise compatibility fallback, inferred transforms versus external geometry gates, forced defaults versus data-quality constraints, duplicate sanitizers versus credential redaction, fixture-tautological tests versus physical outcome rules, duplicated payloads versus frozen ledgers, and batch-wide identity paranoia versus persisted media validation.

Case IDs and prompts are deliberately neutral. Ground-truth labels live in [`evals/adjudication.json`](evals/adjudication.json), which is not copied into the agent workspace. [`evals/grade_case.py`](evals/grade_case.py) applies hidden AST checks, independent behavior calls, fault injection, persistence corruption, remaining-test execution, authorization checks, and a recursive negative-change budget after the agent finishes. Each simplify case has a `golden_after` calibration overlay; each preserve case has a `destructive_mutant` overlay; representative simplify cases also have an `alternate_valid` implementation.

`dev-v1` is retained as historical semantic-deletion safety data. It is not a generic cleanup target and must not be used as the sole tuning objective. The new [`dev-v2-focused`](evals/dev-v2-focused/README.md) development layer is restricted to test bloat (~50%), verification theater (~25%), and defensive/fallback bloat (~25%), with paired preservation counterexamples and three accumulated-slop mini repositories.

No project-level performance score is published. Diagnostics under `evals/results/` are development evidence only; public model-effect claims require repeated, pinned runs against a corpus frozen after the evaluated Skill version, with held-out cases reported separately. Fixture count and passing pre-cleanup tests are not evidence of Skill effectiveness.

See [`evals/README.md`](evals/README.md) for the protocol and metrics.

## Validate locally

The dependency-free validator checks Skill structure, explicit-only policy, neutral prompts, corpus/adjudication agreement, confirmed evidence classes, the manifest-declared 20 fixtures and 37 baseline tests, bidirectional hidden-grader calibration, recursive negative-change enforcement, canonical Skill discovery metadata, and authorization safety:

```bash
python3 scripts/validate_corpus.py
```

Validate the focused accumulated-slop layer separately:

```bash
python3 scripts/validate_focused_corpus.py
```

`agent-skill-eval 0.7.0` installs Codex skills into the legacy `.codex/skills` path. All Codex benchmark commands therefore go through the pinned compatibility wrapper, which switches only Codex to the [current canonical `.agents/skills` path](https://developers.openai.com/codex/skills). Validate the harness format through `uv`:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill skill/deslop \
  --evals evals/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/evals.json
```

Run a real Codex A/B evaluation with a deliberately pinned model and repeated trials:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skill/deslop \
  --evals evals/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 5 \
  --concurrency 1 \
  --baseline \
  --post-grade-command "python3 evals/grade_case.py"
```

Before any `run`, the wrapper verifies that `skill/deslop` matches the suite/frontmatter name, refuses ambient canonical, legacy, or admin `deslop` Skill paths that could contaminate the without-Skill baseline, installs the pure runtime directory into a temporary `.agents/skills/deslop`, and verifies its content hash. It also fixes 0.7.0 worktree side-effect comparison to use pre/post status differences rather than treating pre-existing fixture and Skill status as agent mutations, and deterministically counterbalances A/B submission order by case and run parity. Run published benchmarks with concurrency 1 so submission order is execution order. Run benchmarks from a clean user profile or container; the wrapper never moves user files. The required post-grade hook records successful path/hash verification under `skill_discovery` in `run_meta.json` without adding a scored assertion; discovery failure remains a hard-fail assertion. A run that bypasses the wrapper or hook must not be published as a benchmark result.

Record the model, reasoning effort, Codex version, harness version, run count, token cost, and wall time with every published result.

## Evaluation priorities

Metrics are ordered deliberately:

### A. Semantic decision quality

1. **Behavior Preservation Rate** — proportion of preservation cases that pass hidden contracts.
2. **Simplification Case Recall** — proportion of deletion cases that reach the adjudicated simpler state and pass hidden contracts. This is case-level semantic recall, not a percentage of lines removed.

### B. Reduction magnitude and cost

3. **Test reduction** — test LOC, test count, deterministic test runtime, and expensive fixture/invocation counts.
4. **Verification/fallback reduction** — checksum, receipt, manifest, validator, try/except, compatibility, and fallback machinery removed.
5. **Cleanup-induced additions** — new tests, wrappers, abstractions, dependencies, branches, and production/test LOC.

Reduction magnitude is evaluated only after hidden behavior gates pass. Raw LOC deletion is not success.

A large deletion with a low preservation rate is failure. A cleanup that grows the codebase with new scaffolding is also failure.

Harness mean assertion pass rate is retained only as a within-version diagnostic. Adding another safety gate changes that mean without changing model behavior, so project-level comparisons use the case-level metrics above.

## Repository layout

```text
skill/deslop/                    Pure runtime Skill payload
  SKILL.md                       Core workflow and authorization model
  agents/openai.yaml             UI metadata and explicit-only policy
  references/                    Focused test, trust, fallback, and scientific guidance
evals/evals.json                 agent-skill-eval suite
evals/adjudication.json          Labels, evidence class, and oracle source
evals/calibration/               Positive goldens and destructive mutants
evals/grade_case.py              Hidden post-grade contracts and budget checks
evals/files/                     Neutral paired fixtures copied to agents
evals/dev-v2-focused/            Focused corpus and accumulated-slop mini repos
scripts/validate_corpus.py       Dependency-free static validation
scripts/validate_focused_corpus.py  Focused corpus and mini-repo validation
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
