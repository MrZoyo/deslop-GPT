import unittest

from app import render_manifest


class PublisherContractTests(unittest.TestCase):
    def test_manifest_has_fingerprint(self):
        manifest = render_manifest([{"id": "a"}])
        self.assertEqual(manifest["entries"], [{"id": "a"}])
        self.assertEqual(manifest["count"], 1)
        self.assertEqual(len(manifest["fingerprint"]), 64)


if __name__ == "__main__":
    unittest.main()
