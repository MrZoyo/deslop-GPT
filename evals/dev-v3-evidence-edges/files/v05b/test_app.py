import unittest

from app import render_manifest


PUBLISHED_FINGERPRINT = "3f2d3382920cf76f6c108c87a501b0c6742601774c5db8bd3d71732299a9d852"


class PublisherContractTests(unittest.TestCase):
    def test_manifest_matches_published_fingerprint(self):
        manifest = render_manifest([{"id": "a"}])
        self.assertEqual(manifest["entries"], [{"id": "a"}])
        self.assertEqual(manifest["count"], 1)
        self.assertEqual(manifest["fingerprint"], PUBLISHED_FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
