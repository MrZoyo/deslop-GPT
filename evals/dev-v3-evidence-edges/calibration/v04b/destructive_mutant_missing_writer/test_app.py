import tempfile
import unittest
from pathlib import Path

from app import load_package


MANIFEST = {"size": 13, "sha256": "9d7ec3059a3be4a437e8028d9a498f2fd4adfa7183af52ecc712704ee1dc8260"}


class PackageTests(unittest.TestCase):
    def test_reader(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            path.write_bytes(b"package-bytes")
            self.assertEqual(load_package(path, MANIFEST), b"package-bytes")
