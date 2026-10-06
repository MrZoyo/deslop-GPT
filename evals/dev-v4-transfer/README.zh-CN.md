# 独立 CSV／SQLite 迁移验证案例

**简体中文** · [English](README.md)

这四个夹具在 0.3.4 候选技能固定后，由独立测试设计子代理编写。设计者未读取候选技能、仓库源码、既有用例或历史模型结果。任务只规定生命周期反例和不同存储格式；这是规模有限、刻意成对的迁移验证，不是总体分布的 holdout。

CSV 与 SQLite 各有一个旧版本仍受支持的案例、一个明确退役的案例。每对初始代码相同，由 CONTRACT.txt 明确当前生命周期。隐藏评分器直接使用固定 CSV 字面值或固定 SQL 创建旧数据，不通过候选 writer。检查当前行为、损坏／输入拒绝、有效的存续测试，以及局部自证指纹和退役解码器的删除。规模指标另行报告。

```bash
python3 evals/dev-v4-transfer/held_back/validate_transfer.py
python3 evals/dev-v4-transfer/held_back/grade_transfer.py csv_keep_v1 /path/to/after
```

24 个校准状态均须符合预定的行为、覆盖和删除结果。使用 `--output /checkout外/calibration.json` 保存详细校准记录。被评测模型只接收 manifest 中所选案例的文件，不能读取 `held_back/` 或[设计说明](DESIGN.txt)。不以内部辅助函数名或固定测试数量决定成败。

评测中候选技能保持不变，各版本与案例的分母分开报告，并保留失败及未完成调用。通过此套件不证明任意兼容性、持久性、并发或性能保证；解码器及覆盖检查的具体边界见设计说明。

## 对照期间发现的补充边界

冻结的 draft1 检查漏掉了向已有、带数据、`user_version` 为 0 的 SQLite 数据库写入的情况；两个初始案例都有这个缺陷。[独立的版本 0 探针](../grader-revisions/transfer-existing-v0-v1/README.zh-CN.md) 记录了反例并校准拒绝边界。draft1 的通过状态仅证明其已声明的检查通过；对照报告必须单独披露这项运行期间发现的证据。冻结的 draft1 案例和评分器保持不变。

manifest 描述代理输入。按上方 CLI 在一次性输出副本上显式调用隐藏评分器；manifest 校验不会自动接入或执行评分。通用 harness 接入需要把其 JSON 输出转换为对应的断言格式。本轮原生版本对照使用 checkout 外的独立证据收集器。
