import unittest
from pathlib import Path

from app import build_assets


ROOT = Path(__file__).parent


class AssetCompilerTests(unittest.TestCase):
    def test_compiles_representative_asset(self):
        self.assertEqual(
            build_assets(ROOT / "config.json"),
            {"joint": "hinge", "collision": "door-panel"},
        )


if __name__ == "__main__":
    unittest.main()
