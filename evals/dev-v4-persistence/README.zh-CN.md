# 持久化生命周期反例

**简体中文** · [English](README.md)

`dev-v4-persistence-draft1` 新增两个由契约决定清理边界的 JSON 案例。初始代码相同，当前生命周期契约决定哪个解码路径必须保留。两例都要求清除本地生成的 receipt 和自校验，保留独立输入的摘要校验，以及 format 2 的公开读写契约。

| 案例 | 仍支持的输入 | 清理边界 |
| --- | --- | --- |
| `p01-supported` | Format 1 和 2 | 清除局部自证机制，同时保持两种已有表示可读。 |
| `p01-retired` | 仅 format 2 | 清除已退役的 format 1 路径，并明确拒绝它。 |

隐藏评分器提供独立于候选 writer 的固定落盘输入。编辑后的 writer／reader 能互相配合，不能替代这些检查。另检查无效格式、记录损坏、外部摘要错误、writer 的输出及返回值，以及非零且通过的存续测试。

简化目标要求删掉无用证明字段／哈希，以及明确退役的解码器。新 Python 支持文件、外部依赖、语法错误和生产辅助函数增长会被拒绝；生产／测试规模与测试数另外报告。新语料不继承 rc5 的四行及测试数硬门槛，也不放宽历史分数。校准包含正确清理、另一种有效实现、行为仍正确但清理不足的状态，以及自有测试仍绿却破坏隐藏契约的状态。

不调用模型的验证命令：

```bash
python3 scripts/validate_persistence_corpus.py
python3 evals/dev-v4-persistence/grade_persistence.py p01-supported /path/to/after
```

被评测模型只接收 `evals.json` 中该例的文件。本说明、`evidence.json`、评分器和 `calibration/` 保持隐藏；模型结果与轨迹放在 checkout 外。比较前固定输入、评分器、技能和模型配置，分别记录各版本及重复次数。

[证据记录](evidence.json) 区分原始观察与新明确的契约。这些是暴露开发用例，不表示所有旧文件都必须永久支持，也不建立技能的总体有效性。冻结的 rc5 和 draft4 均未修改。

manifest 描述代理输入。按上方 CLI 在一次性输出副本上显式调用隐藏评分器；manifest 校验不会自动接入或执行评分。通用 harness 接入需要把其 JSON 输出转换为对应的断言格式。本轮原生版本对照使用 checkout 外的独立证据收集器。
