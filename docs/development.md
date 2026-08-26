# Development

This repository separates runtime policy, active evaluation, historical evidence, and presentation material. Keep those boundaries visible in every change.

## Repository layout

| Path | Responsibility |
| --- | --- |
| [`skill/deslop/`](../skill/deslop/) | Self-contained runtime Skill payload |
| [`docs/`](./) | User, design, evidence, and contributor documentation |
| [`evals/dev-v2-focused/`](../evals/dev-v2-focused/) | Active focused development evaluation and graders |
| [`evals/real-world/`](../evals/real-world/) | Manually adjudicated, frozen real-world evidence |
| [`evals/archive/`](../evals/archive/) | Retired evaluation material and historical diagnostics |
| [`scripts/`](../scripts/) | Corpus validation, harness wrapper, and result export tooling |
| [`assets/`](../assets/) | Lightweight repository presentation assets |
| [`.github/workflows/validate.yml`](../.github/workflows/validate.yml) | CI-equivalent repository validation |

## Change boundaries

Treat these as separate products:

- **Runtime Skill:** agent-facing policy and references. Documentation work should normally leave it byte-for-byte unchanged.
- **Active evaluation:** fixtures, manifests, graders, calibration, thresholds, and results. Presentation work must not change its semantics.
- **Real-world input:** exact public source trees. Never format, modernize, or clean a frozen snapshot.
- **Reference evidence:** patches and adjudication. Keep them hidden from any evaluated agent and change them only to correct objective archival errors.
- **Project documentation:** explanatory prose and navigation. It may summarize the other layers but must link to their canonical details instead of inventing a competing source of truth.

## Validation

Run the CI-equivalent checks from the repository root:

```bash
python3 scripts/validate_focused_corpus.py

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill skill/deslop \
  --evals evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/mini-evals.json
```

The retired archive has a separate optional validator:

```bash
python3 scripts/validate_dev_v1_archive.py
```

These commands validate structure and known behavior polarity. They do not run a GPT benchmark or establish model quality.

## Documentation QA

For documentation-only changes:

1. inspect every changed Markdown file as rendered by GitHub-compatible assumptions;
2. verify local links and image targets relative to their source file;
3. verify dynamic badges point to real workflows or repository facts;
4. keep SVG assets self-contained, script-free, and free of remote embeds;
5. search for stale paths and duplicated canonical commands;
6. review claims for implied endorsement, uncontrolled comparisons, or unsupported performance language;
7. compare protected Git tree identities before and after the change.

Do not add a large Markdown framework solely for presentation QA; a focused local link check is sufficient.

## Contributing evidence

The most valuable evaluation contribution has:

- a deletion target with a resolved evidence chain;
- a nearby preservation counterexample;
- an independent behavioral oracle;
- a destructive mutant or other evidence that the preservation gate is meaningful;
- an alternate valid cleanup where practical;
- no dependence on one historical patch shape.

Current-project smells without caller, history, or contract evidence belong in an audit candidate pool, not directly in the scored corpus. Avoid proposing a Skill rule until the pattern repeats and its false-positive boundary is understood.

## Adding a field trial

Follow [Field Trials](field-trials.md). Capture the exact public tree with Git-native mechanisms, keep `input/` separate from `reference/`, record human preservation decisions, and verify that private files never enter the source path. A case-study commit should not silently modify runtime policy or active evaluation semantics.

## Release readiness

Public project releases use semantic versioning beginning with v0.1.0. A `0.x` release is usable but still evolving. Annotated Git tags are immutable release identities. Any future Plugin manifest must use the same version without the leading `v`. Benchmark revision tags remain separate from project releases.

Before a public-facing release commit:

- run CI-equivalent validation;
- verify `skill/`, active evaluation, and frozen inputs against their starting tree identities;
- inspect the full diff and repository status;
- confirm installation guidance against current official Codex documentation;
- avoid stability, adoption, precision, or production claims without a defined policy and evidence;
- keep any distribution metadata aligned with the intended Git release tag.

Do not infer a product version from a benchmark tag or move a published release tag.
