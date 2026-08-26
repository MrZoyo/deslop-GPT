<p align="center">
  <img src="assets/deslop-banner.svg" alt="deslop — deletion-first cleanup for agent-maintained codebases" width="100%">
</p>

<h1 align="center">deslop</h1>

<p align="center">
  <strong>A deletion-first Agent Skill for agent-maintained codebases</strong>
</p>

<p align="center">
  Evidence-backed cleanup that reduces accumulated machinery while preserving real behavior.
</p>

<p align="center">
  <a href="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml"><img src="https://github.com/MrZoyo/deslop-GPT/actions/workflows/validate.yml/badge.svg" alt="Validate workflow"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f.svg?style=flat-square" alt="MIT license"></a>
  <a href="skill/deslop/"><img src="https://img.shields.io/badge/Agent%20Skill-Codex--compatible-0969da.svg?style=flat-square" alt="Codex-compatible Agent Skill"></a>
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
| ~50% | **Test-suite bloat** | Does each test protect distinct external behavior with an independent oracle? |
| ~25% | **Verification theater** | Can the verifier fail independently from the producer, or do both share the same information and failure domain? |
| ~25% | **Defensive / fallback bloat** | Does the recovery path implement a current contract, or merely mask an unexpected internal error? |

Generic dead code, wrappers, abstractions, and comments are secondary. They matter only when they belong to one of these clusters or have direct high-confidence deletion evidence.

## Remove less code. Preserve more meaning.

| Remove | Preserve |
| --- | --- |
| Self-justifying or duplicate tests | Distinct success, rejection, error, and edge-case behavior |
| Checksums, receipts, or validators with no independent consumer | Persistence and corruption checks across a real failure boundary |
| Speculative or obsolete fallback chains | Supported compatibility and documented protocol behavior |
| Repeated defenses inside trusted call graphs | Real handling at external and untrusted boundaries |
| Wrapper/test clusters with no independent purpose | Security, transactions, concurrency, resource, and scientific invariants |

Resemblance to a smell is a lead, not a verdict. Security and trust boundaries, supported callers, persisted formats, and numerical constraints are preserved by default when evidence is incomplete.

## Quick Start

### Install with Codex Skill Installer

Invoke the bundled installer with this GitHub Skill URL:

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/main/skill/deslop
```

For a reviewable local checkout, symlink the runtime directory into Codex's canonical user Skill location:

```bash
git clone https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skill/deslop" "$HOME/.agents/skills/deslop"
```

Codex supports symlinked Skill directories and detects changes automatically. See [Getting Started](docs/getting-started.md) for updates, removal, scoping, and a safer review-first workflow. `deslop` is an independent community project, not an OpenAI product.

The bundled installer may use its legacy `$CODEX_HOME/skills` destination; use the symlink method above when the canonical `$HOME/.agents/skills` path matters.

### Invoke it explicitly

| Invocation | Effect |
| --- | --- |
| `$deslop` | Read-only audit of the established scope |
| `$deslop audit` | Explicit read-only audit |
| `$deslop apply` | Apply reviewed cleanup within scope |
| `$deslop tests apply` | Prioritize test signal and mutual-support test/code clusters |
| `$deslop current branch apply` | Clean current work relative to its actual merge base |
| `$deslop deep` | Repository-wide read-only audit |
| `$deslop deep apply` | Repository-wide cleanup without redesign |

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
- **Production/test asymmetry:** redundant test evidence can be removed without deleting the behavior it observes.
- **Fail-visible bias:** unexpected internal failures should surface unless a concrete recovery or translation contract exists.
- **Subtraction without redesign:** dependencies, abstractions, wrappers, compatibility layers, and replacement scaffolding have a default budget of zero.

The full decision model is documented in [Design](docs/design.md). The frozen runtime [`SKILL.md`](skill/deslop/SKILL.md) remains authoritative for agent behavior.

## Safety model

Invocation is explicit: [`allow_implicit_invocation: false`](skill/deslop/agents/openai.yaml). Default and `audit` modes are read-only, and suspicious constructs can be recorded as deliberate preservation decisions. Code is not removable merely because it looks defensive, was written by an agent, or has a test that could be deleted.

Apply authorization permits scoped edits; it does not resolve uncertainty in favor of deletion. See [Getting Started](docs/getting-started.md) for the review sequence and [Design](docs/design.md) for confidence classes and preserved boundaries.

## Evidence

### Focused development evaluation

[`dev-v2-focused`](evals/dev-v2-focused/README.md) tests preservation and simplification decisions across paired micro cases and three end-to-end miniature repositories. Behavior gates run before reduction metrics. Micro and mini-repository results remain separate, and the repository publishes no project-level performance score.

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
skill/deslop/                    Frozen runtime Skill payload
docs/                            User, design, evidence, and development guides
evals/dev-v2-focused/            Active focused development evaluation
evals/real-world/                Manually adjudicated real-world evidence
evals/archive/                   Retired historical evaluation material
scripts/                         Validation and evaluation tooling
assets/                          README and project presentation assets
```

## Project status and contributing

The project does not yet use semantic versioning and makes no `stable` or `production-ready` claim. The runtime Skill and evaluation evidence are versioned by Git history; benchmark candidates have their own evaluation tags.

The most useful contribution is an evidence-backed case with a nearby preservation counterexample and an independent behavioral oracle—not an isolated snippet that merely looks verbose. Read [Development](docs/development.md) before proposing a Skill policy or evaluation change.

## License

[MIT](LICENSE)
