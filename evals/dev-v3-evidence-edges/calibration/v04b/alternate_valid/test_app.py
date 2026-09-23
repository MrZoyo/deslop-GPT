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
            path.write_bytes(b"package-bytez")
            with self.assertRaises(ValueError):
                load_package(path, MANIFEST)

    def test_write_failure(self):
        original_write = Path.write_bytes

        def partial_write(target, data):
            original_write(target, data[:3])
            raise OSError("disk full")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            path.write_bytes(b"old")
            with patch.object(Path, "write_bytes", autospec=True, side_effect=partial_write):
                with self.assertRaises(OSError):
                    write_package(path, b"package-bytes")
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(list(Path(directory).iterdir()), [path])
