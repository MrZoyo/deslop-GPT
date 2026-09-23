import tempfile
import unittest
from pathlib import Path

from app import _receipt, _verify_receipt, load_package, save_package, write_package


class PackageTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            self.assertIsNone(write_package(path, b"package"))
            self.assertEqual(load_package(path), b"package")

    def test_save_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.bin"
            self.assertIsNone(save_package(path, b"saved"))
            self.assertEqual(path.read_bytes(), b"saved")

    def test_receipt(self):
        self.assertTrue(_verify_receipt(b"package", _receipt(b"package")))

    def test_receipt_field(self):
        self.assertEqual(len(_receipt(b"package")["sha256"]), 64)
