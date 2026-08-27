# deslop documentation

[简体中文](README.zh-CN.md) · **English**

Choose the shortest path that matches what you want to do:

| Goal | Start here |
| --- | --- |
| Install and use `deslop` safely | [Getting Started](getting-started.md) |
| Understand why a cleanup is accepted or preserved | [Design](design.md) |
| Inspect the focused development evidence | [Evaluation](evaluation.md) |
| Inspect real-world case-study methodology | [Field Trials](field-trials.md) |
| Validate, contribute to, or release the repository | [Development](development.md) |

The top-level [README](../README.md) is the public overview. Detailed benchmark mechanics remain canonical under [`evals/`](../evals/README.md), and the self-contained runtime [`SKILL.md`](../skills/deslop/SKILL.md) remains authoritative for agent behavior.

## Documentation boundaries

- `docs/` explains the project to users and contributors.
- `.claude-plugin/` packages the shared runtime for Claude Code and publishes its marketplace entry.
- `skills/deslop/` is the self-contained runtime payload.
- `evals/dev-v2-focused/` is the active development evaluation.
- `evals/real-world/` preserves manually adjudicated historical evidence.

Changing explanatory prose here does not change runtime policy or evaluation semantics.

Maintained project documentation is paired in English and Simplified Chinese. Runtime Skill instructions, frozen evaluation inputs, archived results, and reference evidence remain in their canonical language because translating them would change executable policy or frozen evidence identities.
