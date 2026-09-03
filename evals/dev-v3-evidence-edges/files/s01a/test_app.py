import unittest

from app import load_episode, montage_frames


CURRENT = {"schema": "2.0", "storage": "video", "frames": ["a", "b"]}


class EpisodeReaderTests(unittest.TestCase):
    def test_current_readers(self):
        self.assertEqual(load_episode(CURRENT), ("a", "b"))
        self.assertEqual(montage_frames(CURRENT), ("a", "b"))


if __name__ == "__main__":
    unittest.main()
