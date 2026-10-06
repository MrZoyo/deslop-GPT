# Edge rejection-coverage revision

[简体中文](README.zh-CN.md) · **English**

This opt-in grader revision recognizes `unittest.TestCase.assertRaisesRegex` alongside `assertRaises` and `raises`. It imports the hash-pinned draft4 grader and replaces only its bounded rejection-call recognizer. Behavior, reduction targets, remaining-test requirements, and all numeric growth limits are unchanged. Do not replace historical results with regraded scores.

The original GPT-6.1 diagnostic found two `s01a` outputs with regex-based negative tests that caught a real schema-regression mutant but were missed by the recognizer. Both also failed independent new-test limits; recognizing their coverage does not automatically make the original whole run pass.

```bash
python3 scripts/validate_grader_revision.py
python3 evals/grader-revisions/edge-coverage-v1/grade.py s01a /path/to/after
```

The command also supports the existing `ASE_EVAL_ID`/`ASE_WORKSPACE_PATH` post-grade hook. Validation covers direct and literal-reader-group assertions, actual schema faults, and an absent-negative-coverage state. This is a bounded static recognizer, not a proof of arbitrary helper or dynamic test coverage.
