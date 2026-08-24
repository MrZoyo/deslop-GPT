import tempfile
import unittest
from pathlib import Path

from app import load_episode


class EpisodeReaderTests(unittest.TestCase):
    def test_loads_header_and_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.jsonl"
            path.write_text('{"type":"header","fps":30}\n{"type":"result","passed":true}\n')
            header, result = load_episode(path)
        self.assertEqual(header["fps"], 30)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
