import unittest

from app import summarize_current


class CurrentSummaryTests(unittest.TestCase):
    def test_current_summary(self):
        self.assertEqual(summarize_current([2, 3]), {"count": 2, "total": 5})


if __name__ == "__main__":
    unittest.main()
