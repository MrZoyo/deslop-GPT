# Persistence lifecycle counterexamples

[简体中文](README.zh-CN.md) · **English**

`dev-v4-persistence-draft1` adds two contract-driven JSON cleanup cases. The source code is initially identical; the current lifecycle contract changes which decoder must survive. Both require removal of a locally generated receipt and self-check, preserve independently supplied digest verification, and retain the format 2 public writer/reader contract.

| Case | Supported input | Required cleanup boundary |
| --- | --- | --- |
| `p01-supported` | Formats 1 and 2 | Keep both stored representations readable while removing local proof machinery. |
| `p01-retired` | Format 2 only | Remove the retired format 1 path and visibly reject it. |

The hidden grader supplies fixed stored inputs independently of the candidate writer. A successful edited-writer/edited-reader round trip cannot replace those checks. It also verifies invalid formats, record corruption, external digest mismatches, writer output/return value, and nonzero passing tests.

Reduction requires removal of unused proof fields/hashing and, where retired, the decoder. New Python support files, external dependencies, syntax errors, and production-helper growth are rejected. Production/test size and test counts are reported separately; this new suite does not import rc5's four-line/test-count hard limits or relax its historical scores. Calibration includes golden and alternate cleanups, behavior-preserving insufficient cleanups, and destructive states whose own test suites stay green.

Run without model calls:

```bash
python3 scripts/validate_persistence_corpus.py
python3 evals/dev-v4-persistence/grade_persistence.py p01-supported /path/to/after
```

Copy only the selected case's files from `evals.json` to an evaluated agent. Keep this document, `evidence.json`, the grader and `calibration/` hidden. All model outputs and transcripts belong outside the checkout. Freeze fixture, grader, payload and model settings before comparison; keep versions and repeated calls distinct.

[Evidence record](evidence.json) separates the original observation from the new explicit contracts. These are exposed development cases, not a claim about arbitrary old files or general Skill effectiveness. Neither the frozen rc5 corpus nor draft4 was changed.

The manifest describes agent inputs. Invoke the hidden grader explicitly on a disposable output copy using the CLI shown above; manifest validation does not attach or execute it. A generic harness integration must adapt its JSON output to that harness's assertion schema. The native version comparison used a separate evidence collector outside the checkout.
