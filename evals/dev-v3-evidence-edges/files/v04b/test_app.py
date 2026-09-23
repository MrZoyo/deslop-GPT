import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import load_package, write_package


MANIFEST = {"size": 13, "sha256": "9d7ec3059a3be4a437e8028d9a498f2fd4adfa7183af52ecc712704ee1dc8260"}


class PackageTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            self.assertIsNone(write_package(path, b"package-bytes"))
            self.assertEqual(load_package(path, MANIFEST), b"package-bytes")

    def test_write_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            path.write_bytes(b"old")
            with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    write_package(path, b"package-bytes")
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(list(Path(directory).iterdir()), [path])
