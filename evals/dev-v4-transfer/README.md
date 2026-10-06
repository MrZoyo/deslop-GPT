# Independent CSV and SQLite transfer cases

[简体中文](README.zh-CN.md) · **English**

These four fixtures were authored by an independent test-design agent after the 0.3.4 candidate payload was fixed. The author did not read that payload, repository source, existing cases, or prior model results. The design request specified lifecycle counterexamples and different storage formats; this is a small, deliberately related transfer suite, not a population-level holdout.

CSV and SQLite each have a supported-version case and an explicitly retired-version case. Their code starts identical within each pair; CONTRACT.txt supplies the current lifecycle authority. The hidden grader constructs legacy records from a fixed CSV literal or fixed SQL, never through a candidate writer. It checks current behavior, corruption/input rejection, useful surviving tests, and removal of self-only fingerprints and retired decoders. Size metrics are reported separately.

```bash
python3 evals/dev-v4-transfer/held_back/validate_transfer.py
python3 evals/dev-v4-transfer/held_back/grade_transfer.py csv_keep_v1 /path/to/after
```

All 24 calibration states must match their expected behavior, coverage, and removal outcomes. Use `--output /outside/checkout/calibration.json` to retain calibration details. Copy only the selected manifest entry's files to an evaluated agent; keep `held_back/` and [design notes](DESIGN.txt) outside that workspace. Neither the exact helper names nor a fixed test count determines success.

The candidate stays fixed during evaluation. Report old/new Skill versions and case denominators separately, including failures and incomplete calls. Passing this suite does not prove general compatibility, durability, concurrency, or performance. See the design notes for the bounded decoder and coverage checks.

## Supplementary boundary found during comparison

The frozen draft1 checks missed writes to an existing populated SQLite database whose `user_version` is 0. Both initial fixtures have this defect. [The separate version-0 probe](../grader-revisions/transfer-existing-v0-v1/README.md) records the counterexample and calibrated rejection boundary. Draft1 passing states establish only its declared checks; comparison results must disclose this exploratory finding separately. The frozen draft1 fixtures and grader stay unchanged.

The manifest describes agent inputs. Invoke the hidden grader explicitly on a disposable output copy using the CLI shown above; manifest validation does not attach or execute it. A generic harness integration must adapt its JSON output to that harness's assertion schema. The native version comparison used a separate evidence collector outside the checkout.
