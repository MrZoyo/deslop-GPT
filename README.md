<p align="center">
  <img src="assets/deslop-banner.svg" alt="deslop — deletion-first cleanup for agent-maintained codebases" width="100%">
</p>

<h1 align="center">deslop</h1>

<p align="center">
  <strong>A deletion-first Agent Skill for agent-maintained codebases</strong>
</p>

<p align="center"><a href="README.zh-CN.md">简体中文</a> · <strong>English</strong></p>

<p align="center">
  Evidence-backed cleanup that reduces accumulated machinery while preserving real behavior.
</p>

<p align="center">
  <a href="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml"><img src="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml/badge.svg" alt="Validate workflow"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f.svg?style=flat-square" alt="MIT license"></a>
  <a href="skills/deslop/"><img src="https://img.shields.io/badge/Agent%20Skill-Codex%20%2B%20Claude%20Code-0969da.svg?style=flat-square" alt="Codex and Claude Code compatible Agent Skill"></a>
  <a href="#safety-model"><img src="https://img.shields.io/badge/default-read--only-6e7781.svg?style=flat-square" alt="Read-only by default"></a>
  <a href="evals/real-world/cluster-gpu-monitor/README.md"><img src="https://img.shields.io/badge/field%20trial-manually%20adjudicated-8250df.svg?style=flat-square" alt="Manually adjudicated field trial"></a>
</p>

`deslop` audits and, when explicitly authorized, removes complexity accumulated through repeated coding-agent implementation and correction cycles. Those cycles often leave overlapping regression tests, producer-verifies-producer checks, and fallback layers that hide failures instead of handling a current contract.

This is semantic subtraction, not source beautification. `deslop` is not a formatter, style humanizer, test-count minimizer, blanket ban on defensive code, or automatic permission to edit a repository. It follows justification chains to independent evidence and preserves behavior whose contract remains real or uncertain.

> **Reduce test surface, not behavior surface.**

## What it targets

The percentages below are design priorities, not measured prevalence.

| Priority | Target | Question |
| ---: | --- | --- |
| ~50% | **Test-suite bloat** | Does each test protect a distinct failure domain with a current owner and an independent oracle? |
| ~25% | **Verification theater** | Can the verifier fail independently from the producer, or do both share the same information and failure domain? |
| ~25% | **Defensive / fallback bloat** | Does the recovery path implement a current contract, or merely mask an unexpected internal error? |

Generic dead code, wrappers, abstractions, and comments are secondary. They matter only when they belong to one of these clusters or have direct high-confidence deletion evidence.

## Subtract machinery. Preserve behavior.

| Remove | Preserve |
| --- | --- |
| Self-justifying or duplicate tests | Distinct success, rejection, error, and edge-case behavior |
| Checksums, receipts, or validators with no independent consumer | Persistence and corruption checks across a real failure boundary |
| Speculative or obsolete fallback chains | Supported compatibility and documented protocol behavior |
| Repeated defenses inside trusted call graphs | Real handling at external and untrusted boundaries |
| Wrapper/test clusters with no independent purpose | Security, transactions, concurrency, resource, and scientific invariants |

Resemblance to a smell is a lead, not a verdict. Security and trust boundaries, supported callers, persisted formats, and numerical constraints are preserved by default when evidence is incomplete.

## Quick Start

### Codex: install v0.3.1 as a standalone Skill

Invoke the bundled installer with this GitHub Skill URL:

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.1/skills/deslop
```

For a reviewable local checkout, symlink the runtime directory into Codex's canonical user Skill location:

```bash
git clone --branch v0.3.1 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
```

Codex supports symlinked Skill directories and detects changes automatically. The tagged v0.3.1 path is the current released, pinned standalone Skill; [`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) is the development branch and may contain unreleased changes.

### Claude Code: install the Plugin from GitHub

Inside Claude Code, add this repository as a marketplace and install the Plugin:

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

The canonical Plugin command is `/deslop:deslop`. For a local checkout, load the repository directly with `claude --plugin-dir .` from the repository root. The marketplace catalog is read from `main`, but its Plugin source is pinned to the v0.3.1 tag. This patch release clarifies requirement evidence and host instruction files, adds an active read-only control, and makes the evaluation wrapper host-aware. The v0.3.0 test-first and evidence-edge additions remain unchanged in scope.

### One checkout, standalone discovery on both hosts

The same released runtime payload can be linked into each host's user Skill directory:

```bash
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

Use only the link for the host you need, and run each `ln` command only when its destination does not already exist. A standalone Claude Code installation invokes the Skill as `/deslop`. See [Getting Started](docs/getting-started.md) for installation scope, v0.1.0 migration, updates, removal, and a safer review-first workflow. `deslop` is an independent community project, not an OpenAI or Anthropic product.

### Distribution status

The shared [`skills/deslop/`](skills/deslop/) payload follows the open Agent Skills structure and is used unchanged by Codex and Claude Code. [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) provide Claude Code packaging. Codex Plugin distribution remains withheld because the tested Codex host installed and cached a Skills-only Plugin without registering its bundled Skill; Codex standalone installation remains supported. See the [distribution compatibility note](docs/development.md#distribution-compatibility-note).

### Invoke it explicitly

| Host and distribution | Command name |
| --- | --- |
| Codex standalone Skill | `$deslop` |
| Claude Code standalone Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

Append the same mode and scope arguments to the command name for each host:

| Arguments | Effect |
| --- | --- |
| none | Read-only audit of the established scope |
| `audit` | Explicit read-only audit |
| `apply` | Apply reviewed cleanup within scope |
| `tests apply` | Prioritize test signal and mutual-support test/code clusters |
| `current branch apply` | Clean current work relative to its actual merge base |
| `deep` | Repository-wide read-only audit |
| `deep apply` | Repository-wide cleanup without redesign |

Only `apply` authorizes edits. Staging, commits, pushes, branch changes, resets, and fetching still require separate permission.

## Example workflow

Start with evidence, not edits:

```text
$deslop deep

HIGH
- two fallback layers handle the same internal parse failure;
  current callers and history show no supported legacy input
- a local receipt is produced and verified by the same workflow;
  no external consumer or persisted trust boundary exists

PRESERVE
- a persisted readback detects truncated output across a write/read boundary
- a compatibility branch is required by a documented external protocol
```

Review each evidence chain and preservation decision. Apply only the supported scope:

```text
$deslop deep apply
```

The example is schematic; it does not represent a benchmark fixture or performance claim.

## How deslop decides

- **Independent evidence roots:** current requirements, real callers, public contracts, protocols, trust boundaries, persistence boundaries, or scientific invariants.
- **Closed justification loops:** production code and tests do not become necessary merely by justifying each other.
- **Production reachability and edge closure:** prove the current input-to-consumer path, not only isolated callers or test-injected branches.
- **Production/test asymmetry:** redundant test evidence can be removed without deleting the behavior it observes.
- **Fail-visible bias:** unexpected internal failures should surface unless a concrete recovery or translation contract exists.
- **Subtraction without redesign:** dependencies, abstractions, wrappers, compatibility layers, and replacement scaffolding have a default budget of zero.

The full decision model is documented in [Design](docs/design.md). The self-contained runtime [`SKILL.md`](skills/deslop/SKILL.md) remains authoritative for agent behavior.

## Safety model

Codex enforces explicit invocation through [`allow_implicit_invocation: false`](skills/deslop/agents/openai.yaml). Claude Code does not read that OpenAI-specific metadata; the shared standards-compatible frontmatter instead tells Claude to invoke `deslop` explicitly. Claude Code may still select the Skill from its description, but such an invocation remains read-only unless the user includes `apply`. Default and `audit` modes are read-only, and suspicious constructs can be recorded as deliberate preservation decisions. Code is not removable merely because it looks defensive, was written by an agent, or has a test that could be deleted.

Read-only verification should redirect caches or generated output when practical and disclose incidental residue. Apply authorization permits scoped edits; it does not resolve uncertainty in favor of deletion. See [Getting Started](docs/getting-started.md) for the review sequence and [Design](docs/design.md) for confidence classes and preserved boundaries.

## Evidence

### Validation status

| Runtime payload | Host and path | Runs | What it establishes |
| --- | --- | --- | --- |
| v0.3.1 release payload, pre-release exact hash | Codex subagents loading the Skill by path | 1 default audit plus `t02b` and `t03b` preservation cases | Narrow development regression smoke; all three left fixture content unchanged |
| v0.3.0, exact release hash | Codex subagents loading the Skill by path | 3 mini-repository apply runs plus 1 audit | All three cleaned artifacts passed hidden behavior, reduction, and negative-change gates; no CLI discovery or baseline evidence |
| v0.3.0, exact release hash | Claude Code 2.1.259 local Plugin, Haiku 4.5 | 1 audit plus 1 apply | Plugin loading and one valid cleanup artifact; apply stopped at its turn ceiling before the final report |
| Earlier development payloads | Codex CLI 0.149.1, `gpt-5.6-sol` | rc3 micro, rc4 mini, and targeted rc5 diagnostics | Historical development evidence tied only to those payload hashes |

The two 2026-09-03 forward smokes are published under [`evals/release-smoke/`](evals/release-smoke/). They are exposed, single-run diagnostics without a baseline and are not held-out model-effect evidence. The older rc3 micro pilot measured 63.1% more total tokens and 16.5% more wall time with its then-current Skill; that one-run result does not predict v0.3.x cost, but it supports using `deslop` for deliberate accumulated-slop work rather than routine tiny diffs.

### Focused development evaluation

[`dev-v2-focused`](evals/dev-v2-focused/README.md) tests preservation and simplification decisions across paired micro cases and three end-to-end miniature repositories. Behavior gates run before reduction metrics. Micro and mini-repository results remain separate, and the repository publishes no project-level performance score.

The follow-up [`dev-v3-evidence-edges`](evals/dev-v3-evidence-edges/README.md) draft records 19 anonymized field observations and implements 7 new executable pairs. It is validated as a draft, not reported as model-performance evidence.

See [Evaluation](docs/evaluation.md) for interpretation limits and [`evals/README.md`](evals/README.md) for the canonical protocol.

### Real-world field trials

| Case | Method | Status |
| --- | --- | --- |
| [`cluster-gpu-monitor`](evals/real-world/cluster-gpu-monitor/README.md) | Real repository; read-only audit, human adjudication, then two reviewed cleanup batches | Frozen historical evidence |

The first field trial records both accepted cleanups and deliberate preservation decisions with public before/after provenance. It had no independent baseline run from the same frozen state, so it is not a controlled A/B comparison and does not establish general superiority, 100% precision, or production-proven correctness.

Future cases can be added without becoming Skill-tuning inputs; see [Field Trials](docs/field-trials.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | Choose a user, design, evidence, or development path |
| [Getting Started](docs/getting-started.md) | Installation, invocation modes, scopes, updates, and safe workflows |
| [Design](docs/design.md) | Evidence roots, closed loops, preservation, and subtraction principles |
| [Evaluation](docs/evaluation.md) | Focused corpus, hard gates, run discipline, and interpretation limits |
| [Field Trials](docs/field-trials.md) | Real-world methodology, provenance, isolation, and case registry |
| [Development](docs/development.md) | Repository layout, validation, contribution, and release boundaries |

## Repository structure

```text
.claude-plugin/                 Claude Code Plugin and marketplace metadata
skills/deslop/                   Self-contained runtime Skill payload
docs/                            User, design, evidence, and development guides
evals/dev-v2-focused/            Active focused development evaluation
evals/dev-v3-evidence-edges/     Follow-up evidence-edge draft
evals/runtime-controls/          Authorization and host/runtime controls
evals/release-smoke/             Version-bound forward-smoke records
evals/real-world/                Manually adjudicated real-world evidence
evals/archive/                   Retired historical evaluation material
scripts/                         Validation and evaluation tooling
assets/                          README and project presentation assets
```

## Project status and contributing

Public releases use semantic versioning, beginning with v0.1.0. A `0.x` release is usable but still evolving; it is not a `stable`, `production-ready`, or 1.0-quality claim. Immutable Git tags identify released runtime and distribution states. Benchmark candidates retain their separate evaluation tags.

The most useful contribution is an evidence-backed case with a nearby preservation counterexample and an independent behavioral oracle—not an isolated snippet that merely looks verbose. Read [Development](docs/development.md) before proposing a Skill policy or evaluation change.

## License

[MIT](LICENSE)
