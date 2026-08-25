import unittest

from fixtures import load_records_fixture
from reporting import build_report, publish_report


class CorrectionCycleTwoTests(unittest.TestCase):
    def test_fixture_total_after_total_fix(self):
        self.assertEqual(build_report("run", load_records_fixture()).total, 2)

    def test_fixture_total_is_not_zero(self):
        self.assertGreater(build_report("run", load_records_fixture()).total, 0)

    def test_fixture_total_is_positive_integer(self):
        self.assertIsInstance(build_report("run", load_records_fixture()).total, int)

    def test_fixture_total_matches_label_length(self):
        report = build_report("run", load_records_fixture())
        self.assertEqual(report.total, len(report.labels))


class CorrectionCycleThreeTests(unittest.TestCase):
    def test_alpha_label_survives_publish(self):
        self.assertIn("alpha", publish_report(build_report("run", load_records_fixture()))["labels"])

    def test_beta_label_survives_publish(self):
        self.assertIn("beta", publish_report(build_report("run", load_records_fixture()))["labels"])

    def test_published_labels_are_a_list(self):
        self.assertIsInstance(publish_report(build_report("run", load_records_fixture()))["labels"], list)

    def test_published_labels_are_nonempty(self):
        self.assertTrue(publish_report(build_report("run", load_records_fixture()))["labels"])

    def test_two_fixture_rows_are_stable(self):
        self.assertEqual(len(load_records_fixture()), 2)


class CorrectionCycleFourTests(unittest.TestCase):
    def test_report_title_is_preserved(self):
        self.assertEqual(publish_report(build_report("run", load_records_fixture()))["title"], "run")

    def test_report_mapping_has_title(self):
        self.assertIn("title", publish_report(build_report("run", load_records_fixture())))

    def test_report_mapping_has_total(self):
        self.assertIn("total", publish_report(build_report("run", load_records_fixture())))

    def test_report_mapping_has_labels(self):
        self.assertIn("labels", publish_report(build_report("run", load_records_fixture())))
