import unittest

from app import build_report


class ReportTests(unittest.TestCase):
    def test_report_contains_the_records(self):
        self.assertEqual(build_report([{"name": "a"}]), {"records": [{"name": "a"}]})
