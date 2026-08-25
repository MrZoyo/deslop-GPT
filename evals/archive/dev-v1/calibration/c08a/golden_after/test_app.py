import unittest

from app import generate_report


class ReportTests(unittest.TestCase):
    def test_generated_report_contains_derived_value(self):
        self.assertEqual(generate_report(4), {"value": 4, "doubled": 8})


if __name__ == "__main__":
    unittest.main()
