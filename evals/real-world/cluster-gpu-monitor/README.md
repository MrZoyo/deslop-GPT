# cluster-gpu-monitor real-world field trial

This case preserves a manually adjudicated `$deslop` field trial against the real public repository [MrZoyo/cluster-gpu-monitor](https://github.com/MrZoyo/cluster-gpu-monitor). It is not a synthetic benchmark fixture. The repository had accumulated changes through repeated coding-agent development before `$deslop deep` was run read-only; findings were reviewed by a human before any cleanup was applied.

## Preserved artifacts

The parts of the case have deliberately different roles:

| Artifact | Role |
| --- | --- |
| [`input/`](input/) | Model-visible target repository, frozen at the exact public pre-cleanup tree. |
| [`reference/adjudication.md`](reference/adjudication.md) | Human review record. It is reference-only and must not be exposed during an evaluation. |
| [`reference/batch1.patch`](reference/batch1.patch) and [`reference/batch2.patch`](reference/batch2.patch) | Git-generated reviewed changes. They are reference evidence, not golden patches that a future agent must reproduce exactly. |
| [`../../../skill/deslop/`](../../../skill/deslop/) | Runtime Skill payload. It is outside this case and was not changed or tuned from this field trial. |

The cleanup happened in two reviewed batches. Some findings were applied, while others were deliberately preserved after evidence review because their contracts remained ambiguous or a sound replacement would have required substantial new test infrastructure.

## Provenance and reproduction

The machine-readable details are in [`manifest.json`](manifest.json). On 2026-08-26, the public annotated tags and their peeled targets were independently verified as:

- `deslop-field-trial-before-20260826` → `d9c730275ebaec46c718309ddc34a4bd04ae3938`;
- `deslop-field-trial-reviewed-20260826` → `76760d565fbd816c4a0f5bc3419fef159dbb7d7a`.

`input/` was materialized directly with `git archive d9c730275ebaec46c718309ddc34a4bd04ae3938`. It contains the complete tracked tree from that commit, including the upstream MIT `LICENSE`, and contains no `.git/` directory. No tracked source file was omitted or altered. The private repository and production environment were not source inputs and are not included.

The reviewed reference patches were generated directly from these ranges:

```text
d9c730275ebaec46c718309ddc34a4bd04ae3938..22fb141f7bba3a561b03d9372700f7bffc1e0530
22fb141f7bba3a561b03d9372700f7bffc1e0530..76760d565fbd816c4a0f5bc3419fef159dbb7d7a
```

A future valid cleanup may preserve the same behavior with a different patch shape.

## Evaluation leakage boundary

The reference patches, adjudication, and detailed expected cleanup descriptions are not model-visible evaluation input.

> Any future evaluation using this case must copy/materialize only
> `input/` into an isolated workspace outside the deslop-GPT repository root.
> The evaluated agent must receive the Skill payload and the isolated target
> repository, not the surrounding case-study reference files.

## Interpretation limits

This case is historical, qualitative evidence, not part of the active quantitative benchmark or a Skill-tuning corpus. There was no independent baseline run from the exact same frozen state, so this is not a controlled A/B comparison and cannot establish that the Skill beats a baseline or has general benchmark superiority. One repository also does not justify a new cleanup rule.

The case does provide reproducible evidence for examining the trial's precision, evidence-chain reasoning, and willingness to preserve ambiguous behavior. Those observations must remain bounded to this manually reviewed field trial; they are not claims of 100% precision, statistical validation, or production-proven correctness.
