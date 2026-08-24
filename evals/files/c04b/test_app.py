import unittest

from app import read_actions


class ProtocolCompatibilityTests(unittest.TestCase):
    def test_reads_current_protocol(self):
        self.assertEqual(read_actions({"action": [1, 2]}), [1.0, 2.0])

    def test_reads_supported_legacy_protocol(self):
        self.assertEqual(read_actions({"actions": [3, 4]}), [3.0, 4.0])

    def test_rejects_invalid_action_payload(self):
        with self.assertRaises(TypeError):
            read_actions({"action": "not-a-list"})


if __name__ == "__main__":
    unittest.main()
