import unittest

from app import parse_header


class HeaderProtocolTests(unittest.TestCase):
    def test_current_header(self):
        self.assertEqual(parse_header({"header": "v2"}), "v2")

    def test_supported_legacy_header(self):
        self.assertEqual(parse_header({"legacy_header": "v1"}), "v1")
