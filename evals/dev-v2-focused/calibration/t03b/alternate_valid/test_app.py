import unittest

from app import normalize_identifier


class IdentifierEdgeTests(unittest.TestCase):
    def test_identifier_contracts(self):
        cases = [("", ValueError), (" Straße ", "strasse")]
        for value, expected in cases:
            with self.subTest(value=value):
                if isinstance(expected, type):
                    with self.assertRaises(expected):
                        normalize_identifier(value)
                else:
                    self.assertEqual(normalize_identifier(value), expected)
