import tempfile
import unittest
from pathlib import Path

from reporting import read_persisted_report, validate_report, write_report


class VerificationTests(unittest.TestCase):
    def test_locally_generated_receipt_and_checksum_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            report = write_report(Path(directory) / "report.json", [{"value": 1}])
            self.assertTrue(validate_report(report))
            self.assertIn("receipt", report)

    def test_persisted_external_digest_detects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report = write_report(path, [{"value": 1}])
            external_digest = "ea3e4326939bd91cb481ad506dda2ef92156ad014902647f4d4906c37eab658d"
            self.assertEqual(report["sha256"], external_digest)
            read_persisted_report(path, external_digest)
            path.write_text('{"records": [{"value": 9}]}')
            with self.assertRaises(ValueError):
                read_persisted_report(path, external_digest)

    def test_report_contains_a_checksum_field(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn("sha256", write_report(Path(directory) / "report.json", []))


if __name__ == "__main__":
    unittest.main()
