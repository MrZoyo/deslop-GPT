import unittest

from app import active_camera, camera_from_config


class CameraTests(unittest.TestCase):
    def test_active_camera(self):
        self.assertEqual(active_camera(), {"name": "front", "parent": "head"})

    def test_future_left_camera(self):
        self.assertEqual(
            camera_from_config({"future_left": True}),
            {"name": "left", "parent": "left_wrist"},
        )


if __name__ == "__main__":
    unittest.main()
