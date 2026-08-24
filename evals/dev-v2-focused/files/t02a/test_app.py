import unittest

from app import _normalize_label, public_label


class LabelTests(unittest.TestCase):
    def test_public_label_normalizes_input(self):
        self.assertEqual(public_label("  Alpha   Beta "), "alpha beta")

    def test_private_normalizer_directly(self):
        self.assertEqual(_normalize_label("  Alpha   Beta "), "alpha beta")
