import unittest

from fixtures import load_records_fixture
from reporting import build_report, publish_report


class ReportBehaviorTests(unittest.TestCase):
    def test_published_summary_is_meaningful(self):
        self.assertEqual(
            publish_report(build_report("run", load_records_fixture())),
            {"title": "run", "total": 2, "labels": ["alpha", "beta"]},
        )

    def test_empty_rows_remain_empty(self):
        self.assertEqual(publish_report(build_report("run", [])), {"title": "run", "total": 0, "labels": []})
