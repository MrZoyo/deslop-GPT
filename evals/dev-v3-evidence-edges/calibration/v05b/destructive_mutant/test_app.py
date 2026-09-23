import unittest

from app import render_manifest


class PublisherContractTests(unittest.TestCase):
    def test_manifest_entries_and_count(self):
        manifest = render_manifest([{"id": "a"}])
        self.assertEqual(manifest["entries"], [{"id": "a"}])
        self.assertEqual(manifest["count"], 1)


if __name__ == "__main__":
    unittest.main()
