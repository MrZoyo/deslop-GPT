import unittest

from app import camera_from_active_config


class CameraTests(unittest.TestCase):
    def test_active_camera_configs(self):
        self.assertEqual(
            camera_from_active_config("left"),
            {"name": "left", "parent": "left_wrist"},
        )
        self.assertEqual(
            camera_from_active_config("right"),
            {"name": "right", "parent": "right_wrist"},
        )


if __name__ == "__main__":
    unittest.main()
