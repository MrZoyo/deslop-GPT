import unittest
from pathlib import Path

from app import load_protocol_fixture


FIXTURE = Path(__file__).parent / "fixtures" / "protocol.json"


class ProtocolFixtureTests(unittest.TestCase):
    def test_managed_protocol_fixture(self):
        self.assertEqual(load_protocol_fixture(FIXTURE), ("rgb", "depth", "mask"))


if __name__ == "__main__":
    unittest.main()
