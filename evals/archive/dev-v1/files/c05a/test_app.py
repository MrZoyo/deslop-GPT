import unittest

from app import transform_frame


class OrientationTests(unittest.TestCase):
    def test_explicit_rotation(self):
        self.assertEqual(transform_frame((1, 2, 3), rotate=True), (3, 2, 1))

    def test_explicit_identity(self):
        self.assertEqual(transform_frame((1, 2, 3), rotate=False), (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
