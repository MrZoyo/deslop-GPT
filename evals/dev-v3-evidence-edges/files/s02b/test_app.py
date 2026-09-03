import unittest

from app import parse_report_options


class ReportOptionsTests(unittest.TestCase):
    def test_explicit_display_label(self):
        options = parse_report_options({"display_label": "nightly"})
        self.assertEqual(options.display_label, "nightly")


if __name__ == "__main__":
    unittest.main()
