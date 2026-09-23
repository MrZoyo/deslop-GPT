import unittest

from app import render_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_entries_and_count(self):
        self.assertEqual(render_manifest([]), {"entries": [], "count": 0})
        rendered = render_manifest([{"id": "a"}, {"id": "b"}])
        self.assertEqual(rendered["entries"], [{"id": "a"}, {"id": "b"}])
        self.assertEqual(rendered["count"], 2)


if __name__ == "__main__":
    unittest.main()
