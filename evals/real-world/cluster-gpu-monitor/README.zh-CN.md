# cluster-gpu-monitor 真实世界现场试验

**简体中文** · [English](README.md)

本案例保存了在真实公开仓库 [MrZoyo/cluster-gpu-monitor](https://github.com/MrZoyo/cluster-gpu-monitor) 上进行并经人工裁定的 `$deslop` 现场试验。它不是合成基准测试夹具。该仓库在反复的编码 agent 开发过程中累积了变更；以只读方式运行 `$deslop deep` 后，所有发现均在应用清理前经过人工复核。

## 保存的工件

案例各部分有意承担不同角色：

| 工件 | 角色 |
| --- | --- |
| [`input/`](input/) | 模型可见的目标仓库，冻结于公开的清理前精确文件树。 |
| [`reference/adjudication.md`](reference/adjudication.md) | 人工复核记录。仅作参考，评估时不得暴露。 |
| [`reference/batch1.patch`](reference/batch1.patch) 和 [`reference/batch2.patch`](reference/batch2.patch) | Git 生成并经复核的变更。它们是参考证据，不是未来 agent 必须精确复现的黄金补丁。 |
| [`../../../skills/deslop/`](../../../skills/deslop/) | 运行时 Skill 载荷。它位于本案例之外，未因本次现场试验而修改或调优。 |

清理分两个经过复核的批次进行。部分发现得到应用；另一些则在证据复核后被有意保留，因为其契约仍有歧义，或合理替代方案需要大量新的测试基础设施。

## 来源与复现

机器可读详情见 [`manifest.json`](manifest.json)。2026-08-26，公开附注标签及其剥离后的目标经独立验证为：

- `deslop-field-trial-before-20260826` → `d9c730275ebaec46c718309ddc34a4bd04ae3938`；
- `deslop-field-trial-reviewed-20260826` → `76760d565fbd816c4a0f5bc3419fef159dbb7d7a`。

`input/` 直接通过 `git archive d9c730275ebaec46c718309ddc34a4bd04ae3938` 生成。它包含该提交完整的受跟踪文件树（包括上游 MIT `LICENSE`），且不含 `.git/` 目录。没有遗漏或修改任何受跟踪源文件。私有仓库和生产环境不是来源输入，也未包含在内。

经复核的参考补丁直接由以下范围生成：

```text
d9c730275ebaec46c718309ddc34a4bd04ae3938..22fb141f7bba3a561b03d9372700f7bffc1e0530
22fb141f7bba3a561b03d9372700f7bffc1e0530..76760d565fbd816c4a0f5bc3419fef159dbb7d7a
```

未来有效的清理可以用不同补丁形态保留相同行为。

## 评估泄漏边界

参考补丁、裁定记录及详细的预期清理描述都不是模型可见的评估输入。

> 未来使用本案例进行评估时，只能将 `input/` 复制或实体化到 deslop-GPT 仓库根目录之外的隔离工作区。被评估 agent 应仅获得 Skill 载荷和隔离后的目标仓库，不得接触周边案例研究参考文件。

## 解读限制

本案例是历史性的定性证据，不属于当前定量基准或 Skill 调优语料库。由于没有从完全相同冻结状态进行独立基线运行，它不是受控 A/B 对比，不能证明该 Skill 优于基线或具有普遍基准优势。单个仓库也不足以证明应新增一条清理规则。

本案例确实提供了可复现证据，可用于考察此次试验的精确性、证据链推理，以及保留歧义行为的意愿。这些观察必须限定于本次人工复核的现场试验；它们不构成 100% 精确率、统计验证或生产级正确性的声明。
