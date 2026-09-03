import unittest

from app import run_legacy_episode, summarize_current


def legacy_package_fixture():
    return {"legacy_task_id": "retired-task", "diagnostics": ["old"]}


class CurrentSummaryTests(unittest.TestCase):
    def test_current_summary(self):
        self.assertEqual(summarize_current([2, 3]), {"count": 2, "total": 5})


class LegacyPackageTests(unittest.TestCase):
    def test_legacy_episode(self):
        self.assertTrue(run_legacy_episode(legacy_package_fixture()))


if __name__ == "__main__":
    unittest.main()
