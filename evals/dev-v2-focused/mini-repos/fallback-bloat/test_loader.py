import tempfile
import unittest
from pathlib import Path

from loader import load_items, load_versioned, write_atomically


class LoaderTests(unittest.TestCase):
    def test_current_json_items(self):
        self.assertEqual(load_items('{"items": [1, 2]}'), [1, 2])

    def test_legacy_lines_after_missing_current_field(self):
        self.assertEqual(load_items('{"legacy": "one"}'), ['{"legacy": "one"}'])

    def test_current_versioned_protocol(self):
        self.assertEqual(load_versioned({"version": 2, "items": [1]}), [1])

    def test_documented_legacy_versioned_protocol(self):
        self.assertEqual(load_versioned({"version": 1, "records": [2]}), [2])

    def test_atomic_failure_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.bin"

            def fail(_value: object) -> bytes:
                raise RuntimeError("encode failed")

            with self.assertRaises(RuntimeError):
                write_atomically(path, object(), fail)
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix(".bin.partial").exists())


if __name__ == "__main__":
    unittest.main()
