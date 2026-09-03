import unittest

from app import public_label


class LabelTests(unittest.TestCase):
    def test_public_label_behavior(self):
        self.assertEqual(public_label("  Alpha   Beta "), "alpha beta")

    def test_public_label_is_a_string(self):
        self.assertIsInstance(public_label("Alpha"), str)

    def test_public_label_is_not_empty(self):
        self.assertTrue(public_label("Alpha"))


if __name__ == "__main__":
    unittest.main()
