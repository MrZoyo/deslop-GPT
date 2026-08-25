import unittest

from app import parse_header


class HeaderProtocolTests(unittest.TestCase):
    def test_supported_headers(self):
        cases = [
            ({"header": "v2"}, "v2"),
            ({"legacy_header": "v1"}, "v1"),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(parse_header(payload), expected)
