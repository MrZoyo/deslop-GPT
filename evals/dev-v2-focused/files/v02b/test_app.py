import tempfile
import unittest
from pathlib import Path

from app import load_package, write_package


class PersistedPackageTests(unittest.TestCase):
    def test_independent_manifest_detects_corruption(self):
        manifest = {"size": 13, "sha256": "9d7ec3059a3be4a437e8028d9a498f2fd4adfa7183af52ecc712704ee1dc8260"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            write_package(path, b"package-bytes")
            self.assertEqual(load_package(path, manifest), b"package-bytes")
            path.write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                load_package(path, manifest)
