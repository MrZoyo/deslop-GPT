import unittest

from app import read_name


class NameTests(unittest.TestCase):
    def test_valid_name(self):
        self.assertEqual(read_name({"name": "Ada"}), "Ada")

    def test_missing_name_uses_fallback(self):
        self.assertEqual(read_name({}), "unknown")
