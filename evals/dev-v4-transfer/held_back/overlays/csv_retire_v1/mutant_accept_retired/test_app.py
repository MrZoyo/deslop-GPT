import unittest
from app import decode_item, encode_item


class StockRecords(unittest.TestCase):
    def test_exact_current_output(self):
        self.assertEqual(encode_item("bolt", 3), "stock-v2,bolt,3")

    def test_quoted_item_roundtrip(self):
        self.assertEqual(decode_item(encode_item('part, "B"', 0)),
                         {"item": 'part, "B"', "quantity": 0})

    def test_unicode_current_record(self):
        self.assertEqual(decode_item("stock-v2,齿轮,21"), {"item": "齿轮", "quantity": 21})

    def test_bad_writer_input(self):
        for item, quantity in [("", 2), ("x", -1), ("x", True), ("x", 1.5), ("x\ny", 1)]:
            with self.subTest(item=item, quantity=quantity), self.assertRaises(ValueError):
                encode_item(item, quantity)

    def test_bad_record_shape_and_version(self):
        for text in ["stock-v2,x", "stock-v9,x,1", "stock-v2,x,1\nstock-v2,y,2"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                decode_item(text)

    def test_corrupt_current_quantity(self):
        for text in ["stock-v2,x,-1", "stock-v2,x,1.5", "stock-v2,x,nope"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                decode_item(text)


if __name__ == "__main__":
    unittest.main()
