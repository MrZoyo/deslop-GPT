import unittest

from app import Summary, summarize_records


class SummaryTests(unittest.TestCase):
    def test_summary_reports_count_and_names(self):
        self.assertEqual(
            summarize_records([{"name": "a"}, {"name": "b"}]),
            Summary(count=2, names=("a", "b")),
        )
