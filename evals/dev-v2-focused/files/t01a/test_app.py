import unittest

from app import Summary, summarize_records


class SummaryTests(unittest.TestCase):
    def test_summary_count_matches_records(self):
        self.assertEqual(summarize_records([{"name": "a"}, {"name": "b"}]).count, 2)

    def test_summary_length_matches_count(self):
        summary = summarize_records([{"name": "a"}, {"name": "b"}])
        self.assertEqual(len(summary.names), summary.count)

    def test_summary_is_the_expected_dataclass(self):
        self.assertIsInstance(summarize_records([]), Summary)

    def test_summary_names_are_preserved(self):
        self.assertEqual(summarize_records([{"name": "a"}]).names, ("a",))
