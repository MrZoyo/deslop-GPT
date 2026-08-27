# Field Trials

[简体中文](field-trials.zh-CN.md) · **English**

Real-world field trials preserve what happened when `deslop` was used against an actual public repository. They complement synthetic and miniature evaluations with reviewable provenance, but they are historical case studies—not active tuning inputs or controlled benchmark runs.

## Method

A field trial follows this sequence:

1. Freeze the public target repository at an exact pre-cleanup commit.
2. Run a read-only audit first.
3. Review the evidence chain for every proposed change.
4. Apply only findings supported by current contracts, callers, history, and boundaries.
5. Record explicit preservation decisions alongside accepted cleanups.
6. Preserve reviewed patches and human adjudication as reference-only evidence.
7. Record exact source commits, tags, tree identity, license, capture method, and exclusions.

The method values a justified preservation decision as much as a justified deletion. A suspicious construct is not a missed cleanup merely because it remains.

## Separation from Skill tuning

A single repository cannot establish a repeated failure pattern or justify a general Skill rule. Field-trial evidence therefore remains separate from the runtime payload and active quantitative corpus.

- The runtime Skill must not be tuned to reproduce one trial's reviewed patch.
- Reference patches are not golden solutions; a future valid cleanup may differ structurally.
- Findings must not be generalized into benchmark superiority or precision claims.
- A case may inform future research questions without becoming immediate policy.

## Leakage boundary

Each case separates the model-visible target from reference evidence:

```text
case/
  input/          frozen public target repository
  reference/      reviewed patches and human adjudication
  README.md       provenance, method, and limitations
  manifest.json   machine-readable source identity
```

Any future evaluation must materialize only `input/` into an isolated workspace outside the `deslop-GPT` repository root. The evaluated agent receives the Skill payload and isolated target repository—not the surrounding case README, manifest, patches, adjudication, or detailed expected cleanup descriptions.

This is a documentation boundary for the current case-study format, not a newly added evaluation runner.

## Case registry

| Case | Source | Evidence status | Notes |
| --- | --- | --- | --- |
| [`cluster-gpu-monitor`](../evals/real-world/cluster-gpu-monitor/README.md) | [MrZoyo/cluster-gpu-monitor](https://github.com/MrZoyo/cluster-gpu-monitor) | Frozen historical evidence | Read-only audit, human adjudication, two reviewed batches, and explicit preservation decisions |

### cluster-gpu-monitor limitations

The first case has exact public before/after provenance and a complete frozen input tree. It did not have an independent baseline run from the exact same pre-cleanup state. It therefore cannot establish that the Skill beats a baseline, generalizes to other repositories, has 100% precision, or is production-proven.

Its value is narrower: it preserves evidence for reviewing candidate precision, evidence-chain reasoning, and willingness to leave ambiguous behavior intact.

## Adding a future case

A future field-trial contribution should include:

- a public source and compatible license;
- exact pre-cleanup and reviewed commit identities;
- a complete tracked snapshot captured reproducibly;
- Git-generated reviewed patches;
- concise human adjudication, including preservation decisions;
- explicit exclusion of private repositories, production environments, and credentials;
- the same `input/` versus `reference/` isolation boundary;
- an interpretation section that states whether a comparable baseline exists.

Do not add a grader, score, schema framework, or new Skill rule merely to archive one case.
