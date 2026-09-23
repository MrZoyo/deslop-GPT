import inspect
import unittest

from app import summarize_current


class CurrentSummaryTests(unittest.TestCase):
    def test_current_summary(self):
        self.assertEqual(summarize_current([2, 3]), {"count": 2, "total": 5})

    def test_old_package_call_absent(self):
        self.assertNotIn("run_legacy_episode", inspect.getsource(summarize_current))
