import tempfile
import unittest
from pathlib import Path

from app import validate_persisted_media, write_media


class PersistedMediaTests(unittest.TestCase):
    def test_written_media_passes_independent_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_media(Path(directory), [b"frame-a", b"frame-b"])
            validate_persisted_media(*paths)

    def test_corrupt_media_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            media_path, manifest_path = write_media(Path(directory), [b"frame-a"])
            media_path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                validate_persisted_media(media_path, manifest_path)


if __name__ == "__main__":
    unittest.main()
