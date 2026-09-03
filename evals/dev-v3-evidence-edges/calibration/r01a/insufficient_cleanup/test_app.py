import unittest

from app import active_camera


class CameraTests(unittest.TestCase):
    def test_active_camera(self):
        self.assertEqual(active_camera(), {"name": "front", "parent": "head"})


if __name__ == "__main__":
    unittest.main()
