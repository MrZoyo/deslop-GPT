# Development

[简体中文](development.zh-CN.md) · **English**

This repository separates runtime policy, active evaluation, historical evidence, and presentation material. Keep those boundaries visible in every change.

## Repository layout

| Path | Responsibility |
| --- | --- |
| [`.claude-plugin/`](../.claude-plugin/) | Claude Code Plugin identity and GitHub marketplace catalog |
| [`skills/deslop/`](../skills/deslop/) | Self-contained runtime Skill payload |
| [`docs/`](./) | User, design, evidence, and contributor documentation |
| [`evals/dev-v2-focused/`](../evals/dev-v2-focused/) | Active focused development evaluation and graders |
| [`evals/dev-v3-evidence-edges/`](../evals/dev-v3-evidence-edges/) | Follow-up draft for reachability, hermeticity, authority, and schema boundaries |
| [`evals/runtime-controls/`](../evals/runtime-controls/) | Authorization and host/runtime controls kept outside cleanup-quality scores |
| [`evals/release-smoke/`](../evals/release-smoke/) | Small version-bound forward tests with explicit limitations |
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
python3 scripts/validate_evidence_edges_corpus.py

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py self-test \
  --skill skills/deslop \
  --evals evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v2-focused/mini-evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/dev-v3-evidence-edges/evals.json

uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/runtime-controls/evals.json
```

The retired archive has a separate optional validator:

```bash
python3 scripts/validate_dev_v1_archive.py
```

These commands validate structure and known behavior polarity. They do not run a GPT benchmark or establish model quality.

`validate` also prints strict eval-design warnings. [`evals/runtime-controls/`](../evals/runtime-controls/) answers all of them. The scored corpora keep them deliberately: `dev-v2-focused` is frozen at an immutable benchmark tag, and both it and `dev-v3-evidence-edges` force invocation and judge through hidden post-run graders rather than manifest assertions. Adding a trigger or control case to either would change what the published results measured, so do not silence those warnings there.

Validate the Claude Code distribution separately with the host validator:

```bash
claude plugin validate . --strict
```

For a namespaced runtime smoke test, load the checkout with `claude --plugin-dir .` and invoke `/deslop:deslop audit`. This calls Claude and is not part of the offline CI-equivalent checks.

## Documentation QA

For documentation-only changes:

1. inspect every changed Markdown file as rendered by GitHub-compatible assumptions;
2. verify local links and image targets relative to their source file;
3. verify dynamic badges point to real workflows or repository facts;
4. keep SVG assets self-contained, script-free, and free of remote embeds;
5. search for stale paths and duplicated canonical commands;
6. review claims for implied endorsement, uncontrolled comparisons, or unsupported performance language;
7. validate Claude Plugin and marketplace metadata when distribution guidance changes;
8. compare protected Git tree identities before and after the change.

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

Public project releases use semantic versioning beginning with v0.1.0. A `0.x` release is usable but still evolving. Annotated Git tags are immutable release identities. A distribution manifest version must match its Git release tag without the leading `v`; the Claude Plugin manifest is 0.3.2 and must be released with the matching v0.3.2 tag. Every Plugin-content change must bump the manifest version and move the marketplace pin because Claude Code uses the version as its update key. Write the marketplace source in its explicit `url` plus `ref` form before the release commit is tagged; a `github` shorthand inherits the user's Git transport. After the tag exists, the `main` catalog may add its exact commit SHA without changing the tagged Plugin payload. Benchmark revision tags remain separate from project releases.

Before a public-facing release commit:

- run CI-equivalent validation;
- verify `skills/`, active evaluation, and frozen inputs against their starting tree identities;
- inspect the full diff and repository status;
- confirm installation guidance against current official Codex and Claude Code documentation;
- avoid stability, adoption, precision, or production claims without a defined policy and evidence;
- keep any distribution metadata aligned with the intended Git release tag.

Do not infer a product version from a benchmark tag or move a published release tag.

## Distribution compatibility note

The canonical [`skills/deslop/`](../skills/deslop/) runtime stays standards-compatible and is shared unchanged across hosts. Codex discovers it as a standalone Skill under `.agents/skills`; Claude Code can discover the same directory under `.claude/skills` or through the repository's Claude Plugin. The OpenAI-specific [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml) controls Codex UI metadata and explicit-only invocation and is ignored by Claude Code.

Claude Code packaging is shipped through [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) and [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json). The repository root is the Plugin root, so Claude uses the default `skills/<name>/SKILL.md` scan and exposes the canonical namespaced command `/deslop:deslop`. The manifest declares 0.3.2. The `main` marketplace uses an explicit HTTPS Git source pinned to `v0.3.2` and release commit `0cc15c036b07691c600bda1219b8cc5c197ca3f1`. v0.3.2 clarifies missing-evidence limits in the closed-loop rule.

Codex Plugin packaging is not part of v0.3.2. In a historical Codex CLI 0.149.1 experiment, Plugin Creator accepted a temporary Skills-only manifest with `skills: "./skills/"`, and local discovery, installation, and cache creation succeeded, but a fresh app-server did not register the cached `deslop` Skill. Current [OpenAI Codex Skills documentation](https://developers.openai.com/codex/skills/) supports Plugin-distributed Skills, so that old result describes only the tested host; it is not a current platform limitation. Adding Codex Plugin packaging requires current-host validation and its own release change. The Claude-specific `.claude-plugin/` metadata does not substitute for it.
