import unittest

from app import convert_records


class ConversionTests(unittest.TestCase):
    def test_converts_valid_records(self):
        self.assertEqual(convert_records(["a", "b"], str.encode), [b"a", b"b"])

    def test_failed_conversion_is_not_published(self):
        def encode(value: str) -> bytes:
            if value == "bad":
                raise ValueError("invalid record")
            return value.encode()

        with self.assertRaises(Exception):
            convert_records(["good", "bad"], encode)


if __name__ == "__main__":
    unittest.main()
