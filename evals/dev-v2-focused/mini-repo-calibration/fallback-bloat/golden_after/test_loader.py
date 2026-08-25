import tempfile
import unittest
from pathlib import Path

from loader import load_items, load_versioned, write_atomically


class ContractTests(unittest.TestCase):
    def test_current_and_legacy_versions(self):
        self.assertEqual(load_versioned({"version": 2, "items": [1]}), [1])
        self.assertEqual(load_versioned({"version": 1, "records": [2]}), [2])

    def test_malformed_current_payload_fails_visibly(self):
        with self.assertRaises(Exception):
            load_items("not-json")

    def test_atomic_encoder_failure_cleans_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"
            with self.assertRaises(RuntimeError):
                write_atomically(path, object(), lambda _value: (_ for _ in ()).throw(RuntimeError("failed")))
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix(".bin.partial").exists())
