import unittest

from app import load_episode, montage_frames


CURRENT = {"schema": "2.0", "storage": "video", "frames": ["a", "b"]}


class EpisodeReaderTests(unittest.TestCase):
    def test_current_readers_and_old_montage_rejection(self):
        self.assertEqual(load_episode(CURRENT), ("a", "b"))
        self.assertEqual(montage_frames(CURRENT), ("a", "b"))
        with self.assertRaises(ValueError):
            montage_frames({"schema": "1.0", "storage": "video", "frames": ["old"]})


if __name__ == "__main__":
    unittest.main()
