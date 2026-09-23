import unittest

from app import render_manifest, verify_manifest


class ManifestFingerprintTests(unittest.TestCase):
    def test_fingerprint_round_trips(self):
        self.assertTrue(verify_manifest(render_manifest([{"id": "a"}])))

    def test_fingerprint_field_present(self):
        self.assertIn("fingerprint", render_manifest([]))


if __name__ == "__main__":
    unittest.main()
