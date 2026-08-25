import unittest

from fixtures import load_records_fixture
from reporting import Report, build_report, publish_report


class DefensiveTypeTests(unittest.TestCase):
    def test_build_result_is_not_none(self):
        self.assertIsNotNone(build_report("run", load_records_fixture()))

    def test_build_result_is_report(self):
        self.assertIsInstance(build_report("run", load_records_fixture()), Report)

    def test_published_result_is_not_none(self):
        self.assertIsNotNone(publish_report(build_report("run", load_records_fixture())))

    def test_published_result_is_dict(self):
        self.assertIsInstance(publish_report(build_report("run", load_records_fixture())), dict)

    def test_fixture_rows_are_a_list(self):
        self.assertIsInstance(load_records_fixture(), list)

    def test_fixture_rows_are_nonempty(self):
        self.assertTrue(load_records_fixture())
