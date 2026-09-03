# Getting Started

[简体中文](getting-started.zh-CN.md) · **English**

`deslop` is read-only by default. A safe first use is an audit of a narrow scope, followed by human review; only an invocation containing `apply` authorizes file edits.

## Install

### Codex: released standalone Skill v0.3.1

OpenAI's [Codex Skills documentation](https://developers.openai.com/codex/skills/) documents `$skill-installer` for curated skills and skills from other repositories. Invoke it with this repository URL:

```text
$skill-installer
Install the Skill from:
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.1/skills/deslop
```

The v0.3.1 installable payload is only [`skills/deslop/`](../skills/deslop/), not the evaluation corpus or project documentation. The same payload follows the open Agent Skills structure and can also be discovered directly by Claude Code. It retains the v0.3.0 test-first evidence pass and adds narrower requirement-evidence, host-instruction, and read-only verification guidance. The immutable v0.3.0, v0.2.1, and v0.1.0 payloads remain available at their tagged paths.

The currently bundled `$skill-installer` manages downloaded Skills in an installer-managed location, by default under `$CODEX_HOME/skills` (commonly `~/.codex/skills`). That is current installer behavior, not a permanent public path contract. `$HOME/.agents/skills` below is the documented, directly reviewable user discovery path.

### Reviewable standalone checkout for Codex and Claude Code

Codex discovers personal Skills under `$HOME/.agents/skills`; Claude Code uses `$HOME/.claude/skills`. Both follow symlinked Skill directories. Clone the project outside either discovery tree, then create only the link or links you need:

```bash
git clone --branch v0.3.1 --depth 1 https://github.com/MrZoyo/deslop-GPT.git "$HOME/.local/share/deslop-GPT"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" "$HOME/.claude/skills/deslop"
```

Use only the link for the host you need. Run an `ln` command only when its destination does not already exist. Codex normally detects Skill changes automatically. Claude Code watches existing Skill directories, but if the top-level directory was created after a session started, restart that session. The standalone command names are `$deslop` in Codex and `/deslop` in Claude Code.

This is an independent community Skill. Compatibility does not imply affiliation with or endorsement by OpenAI or Anthropic.

### Claude Code Plugin from GitHub

The repository root is also a Claude Code Plugin and marketplace. Inside Claude Code, add the GitHub repository and install its `deslop` entry:

```text
/plugin marketplace add MrZoyo/deslop-GPT
/plugin install deslop@deslop
```

Invoke the installed Plugin with its canonical namespaced command:

```text
/deslop:deslop audit
```

The marketplace catalog follows `main`, declares Plugin version 0.3.1, and pins the Plugin source to the matching v0.3.1 tag. This keeps new installations on the released runtime even when `main` later contains development work. Because Claude Code uses the manifest version as its update key, future Plugin changes must bump both the version and pinned release ref before installed users can receive them.

For local Plugin development, start Claude Code from this repository with:

```bash
claude --plugin-dir .
```

This loads the same [`skills/deslop/`](../skills/deslop/) payload under the `/deslop:deslop` namespace without installing it.

### Upgrade from v0.2.1

v0.3.1 changes the runtime guidance while keeping the `skills/deslop/` path unchanged. A source checkout installed through a symlink only needs to move to the v0.3.1 tag; the link itself does not change. Reinstall an installer-managed Codex copy from the v0.3.1 URL above. Update an installed Claude Code Plugin with `claude plugin update deslop@deslop`, then restart Claude Code. Users on v0.3.0 or v0.2.x can upgrade directly the same way.

### Upgrade from v0.1.0

The installer does not automatically follow a Git directory rename. Reinstall from:

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.3.1/skills/deslop
```

The old v0.1.0 path was:

```text
https://github.com/MrZoyo/deslop-GPT/tree/v0.1.0/skill/deslop
```

If a source checkout is linked into Codex, first inspect the existing destination:

```bash
test -L "$HOME/.agents/skills/deslop"
readlink "$HOME/.agents/skills/deslop"
```

Only when that output confirms the expected v0.1.0 symlink to `~/.local/share/deslop-GPT/skill/deslop`, remove the symlink itself and recreate it for v0.3.1:

```bash
unlink "$HOME/.agents/skills/deslop"
ln -s "$HOME/.local/share/deslop-GPT/skills/deslop" \
  "$HOME/.agents/skills/deslop"
```

If the destination is a real directory or points somewhere else, stop and review it instead of removing it. v0.1.0 remains supported as immutable history at its original tagged path.

### Development branch

The [`main`](https://github.com/MrZoyo/deslop-GPT/tree/main/skills/deslop) path may contain unreleased changes. Use it only when you intentionally want the development version; use the tagged v0.3.1 path when reproducibility matters.

The standalone runtime path is versioned with the repository: v0.1.0 remains at `skill/deslop/`, while v0.2.0 and later use the canonical `skills/deslop/` path.

### Distribution status

Claude Code packaging is defined by [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json), and the GitHub installation catalog is [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json). These files are Claude-specific and do not replace Codex standalone discovery.

Codex Plugin distribution remains withheld. In the tested Codex CLI 0.149.1 environment, Plugin installation and caching succeeded while native registration of the bundled Skill did not. The tagged standalone path above remains the supported Codex release path.

## Invocation modes

Choose the command name for the active host and distribution:

| Host and distribution | Command name |
| --- | --- |
| Codex standalone Skill | `$deslop` |
| Claude Code standalone Skill | `/deslop` |
| Claude Code Plugin | `/deslop:deslop` |

Append the following arguments to that command name:

| Arguments | Authorization and scope |
| --- | --- |
| none | Read-only audit of the established scope |
| `audit` | Explicit read-only audit |
| `apply` | Modify files within the established scope |
| `tests` | Read-only audit focused on test signal |
| `tests apply` | Apply test-focused cleanup, including justified mutual-support clusters |
| `current branch apply` | Apply cleanup to current work relative to the actual merge base |
| `deep` | Repository-wide read-only audit |
| `deep apply` | Repository-wide cleanup without architectural redesign |
| `path/to/file audit` | Restrict inspection to explicit paths plus minimal contract context |

Only `apply` authorizes edits. It does not authorize fetching, resetting, switching branches, staging, committing, pushing, or creating backups unless those operations are requested separately.

In read-only modes, checks should use no-write flags or temporary cache/output locations when available. If a tool still leaves incidental cache artifacts, the audit should disclose them; if a check cannot avoid changing repository-owned content, skip it and say why.

Codex enforces explicit-only selection through [`agents/openai.yaml`](../skills/deslop/agents/openai.yaml). That file is OpenAI-specific. Claude Code reads the shared standards-compatible `SKILL.md` and may select it from its description; without `apply`, that selection remains read-only. Use `/deslop` or `/deslop:deslop` explicitly when reproducible invocation matters.

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
2. Start with the host's `deslop` command plus `audit`, explicit paths, or `deep`.
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

For a pinned symlink installation, review a newer release and check out its immutable tag; the link does not need to change. If installed through `$skill-installer`, invoke it again with the newer tagged URL and follow its current update prompt. To remove a standalone Skill, remove only the managed or symlinked `deslop` directory from the location where it was installed; keep or delete the separate source checkout according to your own workflow.

For a Claude Code Plugin installation, use `/plugin update deslop@deslop` after refreshing the marketplace, or `/plugin uninstall deslop@deslop` to remove it. Removing the Plugin does not remove a separate standalone link.

## Next steps

- Read [Design](design.md) for the evidence model.
- Read [Evaluation](evaluation.md) before interpreting development results.
- Read [Field Trials](field-trials.md) for real-world evidence boundaries.
