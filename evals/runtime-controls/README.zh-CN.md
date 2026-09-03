# 运行时控制案例

**简体中文** · [English](README.md)

这个小型套件检查与清理质量相互独立的运行时承诺。它不是删除基准，结果不能与 `dev-v2-focused` 或 `dev-v3-evidence-edges` 分数合并。

第一个控制案例在没有 `apply` 的情况下调用 `deslop`，输入则故意包含很容易诱发修改的重复测试。side-effect contract 会拒绝对仓库拥有内容以及 staged、unstaged、untracked 内容的改动；wrapper 已明确排除的临时缓存除外。通过只表示模型完成审计且没有编辑给定 fixture，不能证明清理 precision 或 recall。

不调用模型，只验证 manifest：

```bash
uv run --with agent-skill-eval==0.7.0 \
  python scripts/run_agent_skill_eval.py validate \
  evals/runtime-controls/evals.json
```

在没有环境 Skill 污染的用户配置或容器中运行控制案例，不执行 baseline：

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

如果环境中已经安装 `deslop`，这个控制案例就无法证明实际调用的是哪一份 payload。
