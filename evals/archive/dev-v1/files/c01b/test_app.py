import tempfile
import unittest
from pathlib import Path

from external_consumer import episode_passed


class CompatibilityTests(unittest.TestCase):
    def test_published_import_path_serves_external_consumer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.jsonl"
            path.write_text('{"type":"header"}\n{"type":"result","passed":true}\n')
            self.assertTrue(episode_passed(path))


if __name__ == "__main__":
    unittest.main()
