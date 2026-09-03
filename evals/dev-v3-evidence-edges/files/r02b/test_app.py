import unittest

from app import CURRENT_TASK_ID, run_current_episode


class CurrentProductionPathTests(unittest.TestCase):
    def test_current_package_reaches_state_machine(self):
        self.assertTrue(run_current_episode(CURRENT_TASK_ID))


if __name__ == "__main__":
    unittest.main()
