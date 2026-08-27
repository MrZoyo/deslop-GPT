# cluster-gpu-monitor 真实项目试用记录

**简体中文** · [English](README.md)

本案例完整保留了 `$deslop` 在公开仓库 [MrZoyo/cluster-gpu-monitor](https://github.com/MrZoyo/cluster-gpu-monitor) 上的一次真实试用，以及对应的人工审核结论。它不是人为构造的基准评测样例。该仓库此前经历过多轮编程 Agent 开发，代码中逐渐积累了一些额外机制；项目先以只读方式运行 `$deslop deep`，再由人工逐项复核审计结果，最后才执行获准的清理。

## 保存的材料

案例中的各部分用途不同：

| 材料 | 用途 |
| --- | --- |
| [`input/`](input/) | 供 Agent 处理的目标仓库，完整对应公开仓库清理前的 Git 文件树。 |
| [`reference/adjudication.md`](reference/adjudication.md) | 人工审核记录。仅供事后参考，评测期间不得向 Agent 提供。 |
| [`reference/batch1.patch`](reference/batch1.patch) 和 [`reference/batch2.patch`](reference/batch2.patch) | 由 Git 生成、并经人工复核的改动。它们只是参考证据，不是未来 Agent 必须逐字复现的标准答案。 |
| [`../../../skills/deslop/`](../../../skills/deslop/) | Skill 的运行时文件。它不属于本案例，也没有根据这次试用的结果进行修改或调优。 |

清理分两批执行，每一批都经过人工复核。部分审计建议被采纳；另一些则在查完证据后明确决定不改，因为相关约定仍不清楚，或可靠的替代方案需要新建大量测试基础设施。

## 来源与复现方式

机器可读的详细信息见 [`manifest.json`](manifest.json)。2026 年 8 月 26 日，两个公开附注标签经过独立核对；标签解引用后的提交分别是：

- `deslop-field-trial-before-20260826` → `d9c730275ebaec46c718309ddc34a4bd04ae3938`；
- `deslop-field-trial-reviewed-20260826` → `76760d565fbd816c4a0f5bc3419fef159dbb7d7a`。

`input/` 直接使用 `git archive d9c730275ebaec46c718309ddc34a4bd04ae3938` 导出。它包含该提交下全部由 Git 跟踪的文件，包括上游项目的 MIT `LICENSE`，但不包含 `.git/` 目录。导出过程中没有遗漏或修改任何受跟踪的源文件。私有仓库与生产环境从未作为材料来源，也不在案例中。

两份经复核的参考补丁直接从以下提交范围生成：

```text
d9c730275ebaec46c718309ddc34a4bd04ae3938..22fb141f7bba3a561b03d9372700f7bffc1e0530
22fb141f7bba3a561b03d9372700f7bffc1e0530..76760d565fbd816c4a0f5bc3419fef159dbb7d7a
```

未来只要保留相同的行为，也可以采用结构不同的补丁。

## 防止评测答案泄漏

参考补丁、人工审核记录和详细的预期改法都不能作为 Agent 可见的评测输入。

> 未来使用本案例进行评测时，只能把 `input/` 复制或解包到
> deslop-GPT 仓库之外的隔离工作区。接受评测的 Agent 只能拿到 Skill
> 运行文件和隔离后的目标仓库，不能接触案例目录中的其他参考文件。

## 解读限制

本案例只是定性的历史证据，不属于当前的定量基准评测，也不用于调优 Skill。由于没有从完全相同的清理前状态独立运行基线，它不是受控 A/B 对比，不能证明 Skill 优于基线或在一般基准评测中更强。单个仓库也不足以支撑一条新的通用清理规则。

这个案例的价值在于提供可复现的材料，用来复核当次审计建议是否准确、证据链推理是否可靠，以及面对含义不明确的行为时，Agent 是否愿意选择保留。所有结论都只能限定在这次经人工复核的试用中，不能据此宣称 100% 精确、通过统计验证，或已经证明能在生产环境中正确工作。
