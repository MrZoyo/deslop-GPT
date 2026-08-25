import tempfile
import unittest
from pathlib import Path

from app import freeze_jobs, load_frozen_jobs


class FrozenLedgerTests(unittest.TestCase):
    def test_round_trip_preserves_jobs_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs = [{"job_id": "a", "seed": 1}, {"job_id": "b", "seed": 2}]
            paths = freeze_jobs(Path(directory), jobs)
            self.assertEqual(load_frozen_jobs(*paths), jobs)

    def test_tampered_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_path, manifest_path = freeze_jobs(Path(directory), [{"job_id": "a"}])
            jobs_path.write_text('{"job_id":"other"}\n')
            with self.assertRaisesRegex(ValueError, "frozen manifest"):
                load_frozen_jobs(jobs_path, manifest_path)


if __name__ == "__main__":
    unittest.main()
