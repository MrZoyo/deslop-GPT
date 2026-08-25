import tempfile
import unittest
from pathlib import Path

from reporting import read_persisted_report, write_report


class PersistedReportTests(unittest.TestCase):
    def test_external_digest_protects_readback(self):
        expected = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_report(path, [{"value": 1}])
            self.assertEqual(read_persisted_report(path, expected), [{"value": 1}])
            path.write_text('{"records": [{"value": 9}]}')
            with self.assertRaises(ValueError):
                read_persisted_report(path, expected)
