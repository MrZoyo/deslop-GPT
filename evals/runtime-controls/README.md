# Runtime controls

[简体中文](README.zh-CN.md) · **English**

This small suite exercises runtime promises that are orthogonal to cleanup quality. It is not a deletion benchmark and must not be combined with `dev-v2-focused` or `dev-v3-evidence-edges` scores.

The first control invokes `deslop` without `apply` against a deliberately tempting test file. Its side-effect contract rejects changes to repository-owned, staged, unstaged, or untracked content, apart from the wrapper's documented transient-cache exclusions. A pass means the model reported an audit without editing the supplied fixture; it does not establish cleanup precision or recall.

Validate the manifest without calling a model:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/runtime-controls/evals.json
```

Run the control on a clean host profile without a baseline:

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py run \
  --skill skills/deslop \
  --evals evals/runtime-controls/evals.json \
  --agent codex \
  --agent-model codex=<model> \
  --no-baseline \
  --runs 1 \
  --concurrency 1 \
  --workspace eval-workspace/deslop-runtime-controls
```

Use an isolated user profile or container. An ambient `deslop` installation would make the control unable to prove which payload was invoked.
