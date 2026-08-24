import unittest

from app import normalize_identifier


class IdentifierTests(unittest.TestCase):
    def test_identifier_normalizes_the_public_slug(self):
        self.assertEqual(normalize_identifier("  Device A  "), "device-a")
