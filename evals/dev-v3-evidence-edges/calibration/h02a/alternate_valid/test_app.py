import json
import tempfile
import unittest
from pathlib import Path

from app import build_assets


ROOT = Path(__file__).parent


class AssetCompilerTests(unittest.TestCase):
    def test_compiles_representative_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            (temporary_root / "source.json").write_text((ROOT / "source.json").read_text())
            (temporary_root / "config.json").write_text(
                json.dumps({"source": "source.json", "output": "compiled.json"})
            )
            result = build_assets(temporary_root / "config.json")
            self.assertEqual(result, {"joint": "hinge", "collision": "door-panel"})


if __name__ == "__main__":
    unittest.main()
