import tempfile
import unittest
from pathlib import Path

from app import completed_results


class EpisodeTests(unittest.TestCase):
    def test_completed_results_have_output_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            results = completed_results(Path(directory))
            self.assertTrue(all(item.output_path is not None for item in results))
            for item in results:
                self.assertIsNotNone(item.output_path)
                self.assertTrue(item.output_path.is_dir())


if __name__ == "__main__":
    unittest.main()
