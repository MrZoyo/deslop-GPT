import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app import load_package


class PackageTests(unittest.TestCase):
    def test_loads_declared_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = b'{"release": "r1"}'
            (root / "artifact.json").write_bytes(artifact)
            (root / "component.json").write_text(json.dumps({"parts": 47}))
            descriptor = {
                "artifact": "artifact.json",
                "artifact_sha256": hashlib.sha256(artifact).hexdigest(),
            }
            self.assertEqual(load_package(root, descriptor), {"parts": 47})


if __name__ == "__main__":
    unittest.main()
