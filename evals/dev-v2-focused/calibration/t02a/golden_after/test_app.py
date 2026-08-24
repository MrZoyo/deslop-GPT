import unittest

from app import public_label


class LabelTests(unittest.TestCase):
    def test_public_label_normalizes_input(self):
        self.assertEqual(public_label("  Alpha   Beta "), "alpha beta")
