import unittest

from app import VideoMessage, select_video_frames


class VideoQualityTests(unittest.TestCase):
    def test_selects_nearest_source_indices(self):
        messages = [VideoMessage(0.0, "h264", 10), VideoMessage(40.0, "h264", 11)]
        self.assertEqual(
            select_video_frames(messages, [2.0, 35.0], max_fill_gap_ms=10.0),
            [10, 11],
        )

    def test_rejects_mixed_formats(self):
        messages = [VideoMessage(0.0, "h264", 0), VideoMessage(30.0, "hevc", 1)]
        with self.assertRaisesRegex(ValueError, "consistent"):
            select_video_frames(messages, [0.0], max_fill_gap_ms=10.0)

    def test_rejects_excessive_fill_gap(self):
        with self.assertRaisesRegex(ValueError, "fill-gap"):
            select_video_frames([VideoMessage(0.0, "h264", 0)], [50.0], max_fill_gap_ms=10.0)


if __name__ == "__main__":
    unittest.main()
