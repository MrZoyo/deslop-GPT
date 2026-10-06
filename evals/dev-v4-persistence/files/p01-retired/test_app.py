import json
import tempfile
import unittest
from pathlib import Path

from app import _local_receipt, _receipt_matches, read_report, write_report


RECORDS = [{"value": 1}]
DIGEST = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"


class ReportTests(unittest.TestCase):
    def test_public_persisted_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.assertIsNone(write_report(path, RECORDS))
            self.assertEqual(read_report(path, DIGEST), RECORDS)
            path.write_text('{"format": 2, "records": [{"value": 9}]}')
            with self.assertRaises(ValueError):
                read_report(path, DIGEST)

    def test_previous_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text('{"format": 1, "rows": [{"value": 1}]}')
            self.assertEqual(read_report(path, DIGEST), RECORDS)

    def test_local_receipt_repeats_its_inputs(self):
        self.assertTrue(_receipt_matches(RECORDS, _local_receipt(RECORDS)))

    def test_writer_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_report(path, RECORDS)
            self.assertEqual(json.loads(path.read_text())["receipt"], _local_receipt(RECORDS))


if __name__ == "__main__":
    unittest.main()
