import unittest

from app import ConversionOptions, validate_camera_adapter


class AdapterTests(unittest.TestCase):
    def test_default_options_are_valid(self):
        validate_camera_adapter(ConversionOptions())

    def test_real_frame_contract_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "640x352"):
            validate_camera_adapter(ConversionOptions(frame_size=(640, 480)))


if __name__ == "__main__":
    unittest.main()
