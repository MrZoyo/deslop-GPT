import tempfile
import unittest
from pathlib import Path

from app import read_report, write_report


DIGEST = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"


class ReportTests(unittest.TestCase):
    def test_public_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.assertIsNone(write_report(path, [{"value": 1}]))
            self.assertEqual(read_report(path, DIGEST), [{"value": 1}])
            path.write_text('{"format": 2, "records": [{"value": 9}]}')
            with self.assertRaises(ValueError):
                read_report(path, DIGEST)

    def test_supported_previous_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text('{"format": 1, "rows": [{"value": 1}]}')
            self.assertEqual(read_report(path, DIGEST), [{"value": 1}])
