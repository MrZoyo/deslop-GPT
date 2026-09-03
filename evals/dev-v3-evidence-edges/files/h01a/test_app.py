import json
import unittest
from pathlib import Path

from app import legacy_product_label, public_label


OUTPUT = Path(__file__).parent / "outputs" / "product_space.json"


class LabelTests(unittest.TestCase):
    def test_public_label(self):
        self.assertEqual(public_label({"name": " Alpha "}), "alpha")

    @unittest.skipUnless(OUTPUT.is_file(), "requires a one-off planner output")
    def test_saved_product_space_label(self):
        self.assertEqual(legacy_product_label(json.loads(OUTPUT.read_text())), "alpha")


if __name__ == "__main__":
    unittest.main()
