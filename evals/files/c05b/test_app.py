import unittest

from app import decode_frame


class FrameBoundaryTests(unittest.TestCase):
    def test_explicit_transform_uses_valid_external_metadata(self):
        self.assertEqual(
            decode_frame(b"abc", encoded_format="h264", decoded_size=(640, 352), rotate=True),
            b"cba",
        )

    def test_unknown_format_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "format"):
            decode_frame(b"abc", encoded_format="", decoded_size=(640, 352), rotate=False)

    def test_wrong_pixel_space_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "pixel space"):
            decode_frame(b"abc", encoded_format="h264", decoded_size=(640, 480), rotate=False)


if __name__ == "__main__":
    unittest.main()
