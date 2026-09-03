import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app import load_package


class PackageTests(unittest.TestCase):
    def test_declared_artifact_is_required_and_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = b'{"release": "r1"}'
            artifact_path = root / "artifact.json"
            artifact_path.write_bytes(artifact)
            (root / "component.json").write_text(json.dumps({"parts": 47}))
            descriptor = {
                "artifact": "artifact.json",
                "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
            }
            self.assertEqual(load_package(root, descriptor), {"parts": 47})
            artifact_path.unlink()
            with self.assertRaises((FileNotFoundError, ValueError)):
                load_package(root, descriptor)
            artifact_path.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                load_package(root, descriptor)


if __name__ == "__main__":
    unittest.main()
