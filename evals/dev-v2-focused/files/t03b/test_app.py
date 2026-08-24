import unittest

from app import normalize_identifier


class IdentifierEdgeTests(unittest.TestCase):
    def test_empty_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identifier("")

    def test_unicode_casefold_is_stable(self):
        self.assertEqual(normalize_identifier(" Straße "), "strasse")
