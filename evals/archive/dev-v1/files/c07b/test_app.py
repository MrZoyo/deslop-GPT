import unittest

from app import public_report, sanitize_metadata


class PublicMetadataTests(unittest.TestCase):
    def test_credentials_are_not_exported(self):
        records = {
            "episode": {"config_text": "service_token=private", "source": "recorder"},
            "auth": {"api_token": "also-private"},
        }
        report = public_report(records)
        self.assertNotIn("service_token=private", report)
        self.assertNotIn("also-private", report)
        self.assertIn("config_sha256", report)
        self.assertIn("recorder", report)

    def test_sanitization_is_idempotent(self):
        records = {"episode": {"config_text": "secret", "source": "recorder"}}
        sanitized = sanitize_metadata(records)
        self.assertEqual(sanitize_metadata(sanitized), sanitized)


if __name__ == "__main__":
    unittest.main()
