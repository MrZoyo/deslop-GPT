# Getting Started

`deslop` is explicit and read-only by default. A safe first use is an audit of a narrow scope, followed by human review; only an invocation containing `apply` authorizes file edits.

## Install

### Released standalone Skill: v0.1.0

OpenAI's [Codex Skills documentation](https://developers.openai.com/codex/skills/) documents `$skill-installer` for curated skills and skills from other repositories. Invoke it with this repository URL:

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop
```

The v0.1.0 installable payload is only [`skill/deslop/`](https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop), not the evaluation corpus or project documentation.

The currently bundled `$skill-installer` manages downloaded Skills in an installer-managed location, by default under `$CODEX_HOME/skills` (commonly `~/.codex/skills`). That is current installer behavior, not a permanent public path contract. `$HOME/.agents/skills` below is the documented, directly reviewable user discovery path.

### Canonical user path with a reviewable checkout

Codex discovers personal Skills under `$HOME/.agents/skills` and follows symlinked Skill directories. Clone the project outside the discovery tree, then link only the runtime payload:

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.local/share/deslop-GPT/skill/deslop" "$HOME/.agents/skills/deslop"
```

Run the `ln` command only when the destination does not already exist. Codex normally detects Skill changes automatically; restart Codex if the Skill does not appear.

This is an independent community Skill. Compatibility does not imply affiliation with or endorsement by OpenAI.

### Development branch

The [`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) path may contain unreleased changes. Use it only when you intentionally want the development version; use the tagged v0.1.0 path when reproducibility matters.

The standalone runtime path is versioned with the repository: v0.1.0 remains at `skill/deslop/`, while v0.2.0 and later use the canonical `skills/deslop/` path. Released v0.1.0 users can remain pinned to its immutable tag.

## Invocation modes

| Invocation | Authorization and scope |
| --- | --- |
| `$deslop` | Read-only audit of the established scope |
| `$deslop audit` | Explicit read-only audit |
| `$deslop apply` | Modify files within the established scope |
| `$deslop tests` | Read-only audit focused on test signal |
| `$deslop tests apply` | Apply test-focused cleanup, including justified mutual-support clusters |
| `$deslop current branch apply` | Apply cleanup to current work relative to the actual merge base |
| `$deslop deep` | Repository-wide read-only audit |
| `$deslop deep apply` | Repository-wide cleanup without architectural redesign |
| `$deslop path/to/file audit` | Restrict inspection to explicit paths plus minimal contract context |

Only `apply` authorizes edits. It does not authorize fetching, resetting, switching branches, staging, committing, pushing, or creating backups unless those operations are requested separately.

## Scope behavior

### Explicit paths

Use paths for the smallest review surface:

```text
$deslop src/reporting.py tests/test_reporting.py audit
```

The agent may inspect minimal callers, contracts, history, and tests needed to decide whether evidence is independent. Apply mode stays within the stated paths unless a small adjacent contract change is directly required.

### Current work

Inside Git, `current branch` or an omitted scope means current work relative to its actual local merge base. Staged, unstaged, and untracked work are part of that boundary; `main` is never assumed automatically.

### Repository-wide work

`deep` expands inspection, not authority. In `deep apply`, generated code, vendored dependencies, third-party trees, migrations, lockfiles, and externally generated snapshots remain excluded unless explicitly included or demonstrably repository-owned.

## A review-first workflow

1. Read repository instructions and inspect `git status`.
2. Start with `$deslop audit`, explicit paths, or `$deslop deep`.
3. Review each candidate's external evidence, confidence, and preservation decision.
4. Resolve MEDIUM uncertainty before applying anything.
5. Invoke `apply` only for the supported scope.
6. Run the repository's existing targeted checks, then its documented final validation.
7. Inspect the resulting diff. Stage, commit, or push only as a separate authorized action.

An audit should distinguish candidates from boundaries rather than produce a raw smell list.

```text
HIGH
- redundant internal verifier; producer and verifier share all inputs

PRESERVE
- persisted readback crosses a real write/read failure boundary

UNRESOLVED
- compatibility branch has a caller, but its supported-version contract is unclear
```

Apply only the HIGH finding after confirming the evidence chain. Preserve or investigate the others.

## Update and remove

For a pinned symlink installation, review a newer release and check out its immutable tag; the link does not need to change. If installed through `$skill-installer`, invoke it again with the newer tagged URL and follow its current update prompt. To remove the Skill, remove only the managed or symlinked `deslop` directory from the location where it was installed; keep or delete the separate source checkout according to your own workflow.

## Next steps

- Read [Design](design.md) for the evidence model.
- Read [Evaluation](evaluation.md) before interpreting development results.
- Read [Field Trials](field-trials.md) for real-world evidence boundaries.
