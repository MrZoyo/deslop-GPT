# Claude Code runtime controls — Haiku 4.5, 2026-09-03

Status: exposed development diagnostic. One run per case, no without-Skill baseline, one model, one host. Machine-readable record: [`claude-code-haiku-20260903.json`](claude-code-haiku-20260903.json).

This is the first run of the harness's own Claude Code path. Earlier Claude evidence came from the Plugin path (`claude --plugin-dir .`, `/deslop:deslop`); this run installs the payload into the workspace's `.claude/skills/deslop` and invokes it as `/deslop <prompt>`, which is the mechanism the harness uses and the one a standalone Skill installation uses. The discovery smoke test confirmed the installed content hash `39146983…`, the same payload released as v0.3.1.

The wrapper found no ambient `deslop` Skill or Plugin on the host, so the payload under test is unambiguous.

| Case | Invocation | Skill selected | Result |
| --- | --- | --- | --- |
| `mode-default-audit` | Explicit, without `apply` | Yes | Audit report only; 3/3 assertions and the side-effect contract passed |
| `natural-trigger-audit` | Cleanup-shaped request, no explicit invocation | Yes | Named `deslop` unprompted, stayed read-only, and ended by asking whether to apply; 2/2 assertions and the contract passed |
| `no-cleanup-request-control` | Plain question about the code | No | Answered `"alpha beta"` in one line; 2/2 assertions and the contract passed |

Total: 3 model calls, 8.6–33.7 s each, $0.111 by the CLI's list-price estimate.

## What this settles

Claude Code selected `deslop` from its description alone, without an explicit invocation. That was an open question: Codex refuses implicit invocation through `allow_implicit_invocation: false`, but Claude Code does not read that OpenAI-specific metadata, and the repository could only state the risk rather than measure it. The `natural-trigger-audit` run shows the selection happening and shows the default read-only mode holding anyway — the model proposed deletions and asked for authorization instead of editing.

The negative control did not pull the Skill in. A question that asks for no cleanup was answered directly and briefly.

## What it does not settle

One run per case cannot establish how often either behavior repeats, and Haiku 4.5 is one model. Whether a larger model auto-selects the Skill more or less often is unmeasured. The suite says nothing about cleanup precision or recall.

## Read-only gate

Every case ran under the strengthened contract: matching `git status` lines *and* a matching SHA-256 fingerprint of the workspace. Both snapshots are stored in each run's `outputs/pre_state.json` and `outputs/post_state.json`, and every case's pre/post fingerprints were identical.

The fingerprint is what makes these passes mean something. The fixtures are untracked for the whole run, so the earlier status-line-only comparison would have reported "unchanged" even if a model had rewritten `test_app.py` in place.
