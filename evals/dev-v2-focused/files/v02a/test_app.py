import unittest

from app import process, validate_receipt


class ReceiptTests(unittest.TestCase):
    def test_local_receipt_validates_its_own_result(self):
        report = process(3)
        self.assertTrue(validate_receipt(report))

    def test_receipt_repeats_the_local_output(self):
        report = process(3)
        self.assertEqual(report["receipt"]["output"], report["value"])
