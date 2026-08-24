import tempfile
import unittest
from pathlib import Path

from app import write_atomically


class AtomicWriteTests(unittest.TestCase):
    def test_encoder_failure_cleans_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"

            def fail(_value: object) -> bytes:
                raise RuntimeError("encoder failed")

            with self.assertRaises(RuntimeError):
                write_atomically(path, object(), fail)
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix(".bin.partial").exists())

    def test_success_publishes_complete_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"
            write_atomically(path, "ok", lambda value: str(value).encode())
            self.assertEqual(path.read_bytes(), b"ok")
