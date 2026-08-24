import unittest

from app import build_report, validate_report


class ReportVerificationTests(unittest.TestCase):
    def test_self_generated_checksum_round_trips(self):
        report = build_report([{"name": "a"}])
        self.assertTrue(validate_report(report))

    def test_self_generated_checksum_field_exists(self):
        self.assertIn("checksum", build_report([]))
