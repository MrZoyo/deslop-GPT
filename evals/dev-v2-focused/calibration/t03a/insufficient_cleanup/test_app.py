import unittest

from app import normalize_identifier


class IdentifierTests(unittest.TestCase):
    def test_identifier_strips_spaces(self):
        self.assertEqual(normalize_identifier("  Device A  "), "device-a")

    def test_identifier_lowercases_text(self):
        self.assertEqual(normalize_identifier("Device A"), "device-a")

    def test_identifier_uses_stable_slug_form(self):
        self.assertEqual(normalize_identifier("Device A"), "device-a")
