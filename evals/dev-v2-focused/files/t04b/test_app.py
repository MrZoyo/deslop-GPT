import unittest

from app import export_wire_user


class WireContractTests(unittest.TestCase):
    def test_external_wire_prefix_and_payload(self):
        self.assertEqual(export_wire_user("Ada"), b'USR/1 {"display": "User: Ada"}')
