import tempfile
import unittest
from pathlib import Path

from app import publish_records


class PublicationTests(unittest.TestCase):
    def test_publication_round_trips_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = publish_records([{"name": "a"}], Path(directory) / "records.json")
            self.assertIn('"name": "a"', path.read_text())

    def test_empty_publication_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                publish_records([], Path(directory) / "records.json")
