import unittest

from app import sanitize_metadata


class AdapterSanitizerTests(unittest.TestCase):
    def test_adapter_keeps_the_published_sanitizer_entrypoint(self):
        result = sanitize_metadata(
            {"episode": {"config_text": "token=private", "source": "robot"}}
        )
        self.assertEqual(result["episode"]["config_text"], "<omitted>")
        self.assertEqual(result["episode"]["source"], "robot")
        self.assertEqual(len(result["episode"]["config_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
