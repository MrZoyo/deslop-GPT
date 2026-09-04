# Release smoke records

[简体中文](README.zh-CN.md) · **English**

This directory preserves small, version-bound forward tests performed before or immediately after a release candidate was assembled. Each report records the exact runtime hash, host path, fixture choice, result, and known limitations.

These are exposed development diagnostics. Unless a report explicitly says otherwise, they use one run, known fixtures, and no without-Skill baseline. They do not establish model effect, variance, generalization, or a performance claim.

| Payload | Report | Machine-readable record |
| --- | --- | --- |
| v0.3.2 candidate | [`v0.3.2-candidate-cross-version-smoke-20260904.md`](v0.3.2-candidate-cross-version-smoke-20260904.md) | [`JSON`](v0.3.2-candidate-cross-version-smoke-20260904.json) |
| v0.3.1 candidate | [`v0.3.1-candidate-forward-smoke-20260903.md`](v0.3.1-candidate-forward-smoke-20260903.md) | [`JSON`](v0.3.1-candidate-forward-smoke-20260903.json) |
| v0.3.0 release | [`v0.3.0-forward-smoke-20260903.md`](v0.3.0-forward-smoke-20260903.md) | [`JSON`](v0.3.0-forward-smoke-20260903.json) |
