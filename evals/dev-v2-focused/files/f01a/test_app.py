import json
import unittest

from app import load_items


class LoaderTests(unittest.TestCase):
    def test_current_json_payload(self):
        self.assertEqual(load_items('{"items": [1, 2]}'), [1, 2])

    def test_invalid_current_json_fails_visibly(self):
        with self.assertRaises(json.JSONDecodeError):
            load_items("one\ntwo\n")
