import tempfile
import unittest
from pathlib import Path

from app import completed_results


class EpisodeTests(unittest.TestCase):
    def test_completed_results_create_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            results = completed_results(Path(directory))
            for item in results:
                self.assertTrue(item.output_path.is_dir())


if __name__ == "__main__":
    unittest.main()
