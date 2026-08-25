import unittest

from app import load_items


class ProtocolTests(unittest.TestCase):
    def test_supported_versions(self):
        cases = [
            ({"version": 2, "items": [1]}, [1]),
            ({"version": 1, "records": [2]}, [2]),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(load_items(payload), expected)

    def test_unknown_version_is_rejected(self):
        with self.assertRaises(ValueError):
            load_items({"version": 0, "items": []})
