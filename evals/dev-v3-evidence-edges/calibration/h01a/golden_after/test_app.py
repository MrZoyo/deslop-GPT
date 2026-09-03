import unittest

from app import public_label


class LabelTests(unittest.TestCase):
    def test_public_label(self):
        self.assertEqual(public_label({"name": " Alpha "}), "alpha")


if __name__ == "__main__":
    unittest.main()
