import unittest

from app import load_items


class ProtocolTests(unittest.TestCase):
    def test_current_protocol(self):
        self.assertEqual(load_items({"version": 2, "items": [1]}), [1])

    def test_documented_legacy_protocol(self):
        self.assertEqual(load_items({"version": 1, "records": [2]}), [2])

    def test_unknown_protocol_fails(self):
        with self.assertRaises(ValueError):
            load_items({"version": 0, "items": []})
