# Existing SQLite version 0 follow-up

[简体中文](README.zh-CN.md) · **English**

This supplementary counterexample was identified during the frozen 0.3.3/0.3.4 comparison, after a cleanup agent distinguished a new database from an existing database whose `user_version` is 0. It is exploratory follow-up evidence, not a predeclared endpoint of `dev-v4-transfer-draft1`.

Both SQLite contracts require writes to existing unknown-version databases to fail without changing their rows or version. The initial implementation admits versions 0 and 2 without checking whether version 0 belongs to an existing database. With an existing `inventory_items` table, a write deletes its previous rows and changes the version to 2. The draft1 hidden checks exercise unknown version 9 but miss this version 0 case; its known-passing overlays are therefore not proof of the entire written contract.

`probe.py` constructs a populated version 0 database independently of the candidate writer. It requires `ValueError` and unchanged rows/version. Separate new/current write-and-read checks reject an implementation that simply refuses every write. Calibration checks both original fixtures, guarded alternatives, and reject-all mutants (six states) without editing any fixture.

```bash
python3 evals/grader-revisions/transfer-existing-v0-v1/probe.py --calibrate
python3 evals/grader-revisions/transfer-existing-v0-v1/probe.py /path/to/copied/workspace
```

Keep this result separate from draft1 scores and disclose that it was discovered during the run. Apply it equally to originals and both version arms. It does not change the frozen fixtures, grader, candidate payload, or completed trajectories. The probe runs trusted local fixture code and uses temporary databases; it is not a security sandbox or a full SQLite compatibility suite. A future scored corpus revision must explicitly include this boundary and correct its calibrated reference states before collecting new model calls.
