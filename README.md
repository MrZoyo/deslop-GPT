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

The active development layer is [`dev-v2-focused`](evals/dev-v2-focused/README.md): 4 test-bloat pairs, 2 verification-theater pairs, 2 defensive/fallback pairs, and three accumulated-slop mini repositories. Every deletion case has a preservation counterexample and alternate-valid calibration.

The broad 20-case [`dev-v1` archive](evals/archive/dev-v1/) is retained only for historical results and broad safety-regression reference. It contains generic cleanup cases that are intentionally not current tuning targets; active CI and model experiments do not run it.

No project-level performance score is published. Historical diagnostics under `evals/archive/dev-v1/historical-results/` are development evidence only; public model-effect claims require repeated, pinned runs against a corpus frozen after the evaluated Skill version, with held-out cases reported separately. Fixture count and passing pre-cleanup tests are not evidence of Skill effectiveness.

See [`evals/README.md`](evals/README.md) for the protocol and metrics.

## Validate locally

The active dependency-free validator checks the focused Skill/corpus structure, paired behavior polarity, alternate-valid states, mini-repository behavior gates, and reduction-metric eligibility:

```bash
python3 scripts/validate_focused_corpus.py
```

Optionally validate the retired broad safety archive:

```bash
python3 scripts/validate_dev_v1_archive.py  # optional historical check
```

`agent-skill-eval 0.7.0` installs Codex skills into the legacy `.codex/skills` path. All Codex benchmark commands therefore go through the pinned compatibility wrapper, which switches only Codex to the [current canonical `.agents/skills` path](https://developers.openai.com/codex/skills). Validate the harness format through `uv`:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill skill/deslop \
  --evals evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate evals/dev-v2-focused/evals.json
```

Run a real Codex A/B evaluation with a deliberately pinned model and repeated trials:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skill/deslop \
  --evals evals/dev-v2-focused/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --reasoning-effort medium \
  --runs 5 \
  --concurrency 1 \
  --baseline \
  --post-grade-command "python3 evals/dev-v2-focused/grade_focused.py"
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
evals/dev-v2-focused/            Active focused corpus and mini repos
evals/archive/dev-v1/            Retired broad safety corpus and historical results
scripts/validate_focused_corpus.py  Focused corpus and mini-repo validation
scripts/validate_dev_v1_archive.py Optional historical archive validation
  scripts/run_agent_skill_eval.py  Pinned canonical-path compatibility wrapper
```

Focused fixtures live under `evals/dev-v2-focused/files/`; the retired broad fixtures live under `evals/archive/dev-v1/files/`.

## Contributing

The most valuable contribution is a small paired case with adjudicated evidence:

- one fixture where a construct should be removed;
- one nearby counterexample where it must be preserved;
- an independent behavioral oracle;
- deterministic assertions that expose both over-preservation and over-deletion.

Current-project smells without historical or contract evidence belong in an audit candidate pool, not the scored corpus. Avoid adding a rule without a false-positive case.

## License

[MIT](LICENSE)
