import unittest

from app import verify_episode


class OutcomeTests(unittest.TestCase):
    def valid(self, **overrides):
        values = {
            "events": ["release", "clearance", "target", "settle"],
            "final_angle": 1.1,
            "target_angle": 1.0,
            "numeric_ok": True,
            "rebound": 0.01,
            "rebound_limit": 0.05,
        }
        values.update(overrides)
        return verify_episode(**values)

    def test_valid_physical_outcome(self):
        self.assertTrue(self.valid())

    def test_final_angle_does_not_hide_wrong_event_order(self):
        with self.assertRaisesRegex(ValueError, "physical order"):
            self.valid(events=["target", "release", "clearance", "settle"])

    def test_numerical_failure_is_a_hard_failure(self):
        with self.assertRaisesRegex(ValueError, "numerical"):
            self.valid(numeric_ok=False)

    def test_rebound_is_a_hard_failure(self):
        with self.assertRaisesRegex(ValueError, "rebounded"):
            self.valid(rebound=0.2)


if __name__ == "__main__":
    unittest.main()
