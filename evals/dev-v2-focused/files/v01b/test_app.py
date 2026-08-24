import tempfile
import unittest
from pathlib import Path

from app import verify_artifact, write_artifact


class ArtifactBoundaryTests(unittest.TestCase):
    def test_external_digest_accepts_the_published_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.bin"
            write_artifact(path, b"public-fixture")
            self.assertEqual(
                verify_artifact(path, "26717ae4369d005dc210693d1d9256de56b5689078ed07922317ea56020a6486"),
                b"public-fixture",
            )
