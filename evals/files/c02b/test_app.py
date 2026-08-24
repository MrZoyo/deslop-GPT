import tempfile
import unittest
from pathlib import Path

from app import publish_episode


class PublicationTests(unittest.TestCase):
    def test_success_is_published_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = publish_episode(root, lambda: b"complete")
            self.assertEqual(target.read_bytes(), b"complete")
            self.assertFalse((root / "episode.bin.partial").exists())

    def test_failure_removes_partial_output_and_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def fail() -> bytes:
                raise RuntimeError("encoder failed")

            with self.assertRaisesRegex(RuntimeError, "encoder failed"):
                publish_episode(root, fail)
            self.assertFalse((root / "episode.bin.partial").exists())
            self.assertFalse((root / "episode.bin").exists())


if __name__ == "__main__":
    unittest.main()
