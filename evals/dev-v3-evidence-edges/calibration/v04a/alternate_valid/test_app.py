import tempfile
import unittest
from pathlib import Path

from app import load_package, save_package, write_package


class PackageTests(unittest.TestCase):
    def test_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            self.assertIsNone(write_package(path, b"first"))
            self.assertEqual(load_package(path), b"first")

    def test_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            self.assertIsNone(save_package(path, b"second"))
            self.assertEqual(load_package(path), b"second")
