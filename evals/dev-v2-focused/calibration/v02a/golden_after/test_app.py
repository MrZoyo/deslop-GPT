import unittest

from app import process


class ProcessTests(unittest.TestCase):
    def test_process_returns_the_computed_value(self):
        self.assertEqual(process(3), 6)
