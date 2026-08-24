import unittest

from reporting import Report, _coerce_label, build_report, publish_report


ROWS = [{"label": " alpha "}, {"label": "beta"}]


class ReportTests(unittest.TestCase):
    def test_report_publishes_meaningful_summary(self):
        self.assertEqual(
            publish_report(build_report("run", ROWS)),
            {"title": "run", "total": 2, "labels": ["alpha", "beta"]},
        )

    def test_report_total_matches_rows(self):
        self.assertEqual(build_report("run", ROWS).total, 2)

    def test_report_labels_length_matches_total(self):
        report = build_report("run", ROWS)
        self.assertEqual(len(report.labels), report.total)

    def test_report_is_a_report_instance(self):
        self.assertIsInstance(build_report("run", ROWS), Report)

    def test_report_labels_are_not_none(self):
        self.assertIsNotNone(build_report("run", ROWS).labels)

    def test_private_label_helper_directly(self):
        self.assertEqual(_coerce_label(" alpha "), "alpha")

    def test_published_total_is_an_integer(self):
        self.assertIsInstance(publish_report(build_report("run", ROWS))["total"], int)


if __name__ == "__main__":
    unittest.main()
