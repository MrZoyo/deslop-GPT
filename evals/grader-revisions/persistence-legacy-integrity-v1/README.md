# Supported legacy JSON integrity probe v1

[简体中文](README.zh-CN.md) · **English**

An independent release review on 2026-10-06 found a blind spot in the frozen `dev-v4-persistence-draft1` grader: format 1 receives a valid-read check, but corruption and wrong-digest checks exercise only format 2. An early return of the legacy rows can therefore bypass the required external digest and still pass draft1 and the retained suite.

This separate post-run probe applies only to `p01-supported`. It checks a fixed valid legacy artifact, changed legacy rows, and a wrong legacy digest. Valid legacy reads and current writes/reads must also succeed, so rejecting everything cannot pass. Calibration covers the original, both valid cleanup overlays, the green-suite early-return mutant, and a reject-all mutant. The original grader, fixtures, and comparison scores remain unchanged.

```bash
python3 evals/grader-revisions/persistence-legacy-integrity-v1/probe.py --calibrate
python3 evals/grader-revisions/persistence-legacy-integrity-v1/probe.py /path/to/copied-p01-supported-output
```

The reviewer checked all six saved supported-case outputs from the 0.3.3/0.3.4 comparison; none accepted corrupt legacy rows. Report any results from this probe as supplementary, applied symmetrically to both arms, rather than adding them to the predeclared denominator. This small probe does not establish complete integrity coverage.
