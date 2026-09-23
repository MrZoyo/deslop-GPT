import unittest

from app import render_manifest


class ManifestFingerprintTests(unittest.TestCase):
    def test_fingerprint_field_present(self):
        self.assertIn("fingerprint", render_manifest([]))


if __name__ == "__main__":
    unittest.main()
