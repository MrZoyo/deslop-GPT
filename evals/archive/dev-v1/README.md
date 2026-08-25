# Archived `dev-v1`

`dev-v1` is retired from active benchmark and Skill-tuning workflows. It remains in the repository as historical semantic-deletion safety data and a source of broad false-positive regression cases.

## Contents

- `evals.json` / `adjudication.json`: the original 20 semantic cases plus audit control;
- `files/`: neutral fixtures;
- `calibration/`: golden, mutant, and alternate-valid states;
- `grade_case.py`: the historical hidden grader;
- `historical-results/`: transcript-free pilot records and reports.

The corpus includes generic dead-helper, wrapper, abstraction, and duplication cases that are intentionally outside the current `deslop` target. Do not use it as an active tuning objective or combine its scores with `dev-v2-focused`.

## Historical result

The full pilot recorded a mixed result: baseline preservation 10/10 versus Skill 7/10, and simplification case recall 6/10 versus 8/10. The result is diagnostic history, not an effectiveness claim. See [`historical-results/dev-v1-full-pilot-20260825.md`](historical-results/dev-v1-full-pilot-20260825.md).

## Optional archive validation

The old polarity/calibration validator remains available as a manual check:

```bash
python3 scripts/validate_dev_v1_archive.py
```

It is deliberately not part of pull-request active CI. The active benchmark and validation entry point is [`../../dev-v2-focused/README.md`](../../dev-v2-focused/README.md).

Historical source state is also preserved by the repository history and the `dev-v1-final` tag when that tag is created.
