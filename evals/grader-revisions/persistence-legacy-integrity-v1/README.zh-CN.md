# 受支持旧 JSON 格式的完整性探针 v1

**简体中文** · [English](README.md)

2026-10-06 的独立发布审核发现，冻结的 `dev-v4-persistence-draft1` 评分器只检查格式 1 的正常读取，损坏数据和错误摘要仅覆盖格式 2。因此，旧格式分支直接返回 rows、绕过契约要求的外部摘要检查，也能通过 draft1 和剩余测试。

这份运行后追加的独立探针仅适用于 `p01-supported`：分别检查固定的合法旧文件、被修改的旧格式数据和错误的旧格式摘要；合法旧文件读取及当前写入/读取也必须成功，防止一律拒绝的实现过关。校准包含原始状态、两种合法清理、剩余测试仍通过的提前返回变异体，以及一律拒绝的变异体。原评分器、输入和比较分数保持不变。

```bash
python3 evals/grader-revisions/persistence-legacy-integrity-v1/probe.py --calibrate
python3 evals/grader-revisions/persistence-legacy-integrity-v1/probe.py /path/to/copied-p01-supported-output
```

审核者检查了 0.3.3/0.3.4 比较中保存的全部 6 份受支持格式输出，没有发现接受损坏旧数据的输出。探针结果应对两组对称计算并单列为补充证据，不加入预先声明的分母。这份小探针不能证明完整性检查已被全面覆盖。
