import tempfile
import unittest
from pathlib import Path

from app import generate_report


class ReportTests(unittest.TestCase):
    def test_generated_report_contains_derived_value(self):
        self.assertEqual(generate_report(4), {"value": 4, "doubled": 8})

    def test_unused_workspace_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
