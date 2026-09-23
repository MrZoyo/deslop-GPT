import unittest

from app import load_episode, montage_frames


CURRENT = {"schema": "2.0", "storage": "video", "frames": ["a", "b"]}


class EpisodeReaderTests(unittest.TestCase):
    def test_current_readers(self):
        stale = dict(CURRENT, schema="1.0")
        for reader in (load_episode, montage_frames):
            with self.subTest(reader=reader.__name__):
                self.assertEqual(reader(CURRENT), ("a", "b"))
                with self.assertRaises(ValueError):
                    reader(stale)


if __name__ == "__main__":
    unittest.main()
