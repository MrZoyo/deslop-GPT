import unittest

from app import render_manifest


class ManifestTests(unittest.TestCase):
    def test_renders_entries_and_count(self):
        self.assertEqual(render_manifest([{"id": "a"}]), {"entries": [{"id": "a"}], "count": 1})


if __name__ == "__main__":
    unittest.main()
