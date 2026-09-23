import tempfile
import unittest
from pathlib import Path

from app import load_package, save_package, write_package


class PackageTests(unittest.TestCase):
    def test_public_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            for writer in (write_package, save_package):
                self.assertIsNone(writer(path, b"package"))
                self.assertEqual(load_package(path), b"package")
