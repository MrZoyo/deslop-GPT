# SQLite 已有版本 0 数据库反例

**简体中文** · [English](README.md)

这个补充反例是在冻结后的 0.3.3/0.3.4 对照期间发现的：一个清理代理区分了新建数据库和 `user_version` 为 0 的已有数据库。它属于运行期间发现的补充证据，不是 `dev-v4-transfer-draft1` 预先声明的评分项。

两个 SQLite 契约都要求拒绝向未知版本的已有数据库写入，并保留原有数据和版本。初始实现直接允许版本 0 和 2，没有区分版本 0 数据库是否已经存在。如果其中已有 `inventory_items` 表，写入会删除原有行并把版本改为 2。draft1 的隐藏检查覆盖未知版本 9，却漏掉了版本 0；其通过校准的参考状态不能证明整个文字契约都已满足。

`probe.py` 独立构造带数据的版本 0 数据库，要求写入抛出 `ValueError`，且数据和版本不变。另有新建及当前格式的读写检查，防止“拒绝所有写入”误通过。校准验证两个初始实现、加入版本 0 保护的变体和拒绝所有写入的破坏变体，共六个状态；不会修改原始案例。

```bash
python3 evals/grader-revisions/transfer-existing-v0-v1/probe.py --calibrate
python3 evals/grader-revisions/transfer-existing-v0-v1/probe.py /path/to/copied/workspace
```

该结果必须与 draft1 分数分开，并注明是在运行期间发现的；应同等检查原始实现及两个版本的输出。它不改变冻结的案例、评分器、候选技能和已完成轨迹。脚本执行可信本地案例并使用临时数据库，不是安全沙箱或完整 SQLite 兼容性测试。后续评分语料若纳入这个边界，需要先明确修订契约检查和校准参考，再收集新的模型调用。
