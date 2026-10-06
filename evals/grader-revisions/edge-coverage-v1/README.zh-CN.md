# 边界拒绝覆盖识别修订

**简体中文** · [English](README.md)

此可选评分修订在 `assertRaises`、`raises` 之外识别 `unittest.TestCase.assertRaisesRegex`。它导入哈希固定的 draft4 评分器，只替换有界的拒绝调用识别函数。行为、简化目标、存续测试要求和全部数值增长门槛保持不变。重新评分的结果另立记录，不替换历史分数。

GPT-6.1 诊断中的两个 `s01a` 结果有正确的正则异常断言，并能捕获真实 schema 回退，却被原识别器漏掉。它们还分别违反新增测试限制；修正覆盖识别并不自动令整次运行通过。

```bash
python3 scripts/validate_grader_revision.py
python3 evals/grader-revisions/edge-coverage-v1/grade.py s01a /path/to/after
```

命令也支持既有 `ASE_EVAL_ID`／`ASE_WORKSPACE_PATH` post-grade hook。校准覆盖直接调用、字面值 reader 分组、真实 schema 故障及缺少负向覆盖的状态。它仍是有界静态识别器，不能证明任意辅助函数或动态测试的覆盖。
