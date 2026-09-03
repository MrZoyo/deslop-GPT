import json
import tempfile
import unittest
from pathlib import Path

from app import build_assets


ROOT = Path(__file__).parent


class AssetCompilerTests(unittest.TestCase):
    def test_compiles_representative_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            config = json.loads((ROOT / "config.json").read_text())
            config["output"] = str(Path(directory) / "compiled.json")
            config_path = Path(directory) / "config.json"
            config["source"] = str(ROOT / "source.json")
            config_path.write_text(json.dumps(config))
            self.assertEqual(
                build_assets(config_path),
                {"joint": "hinge", "collision": "door-panel"},
            )


if __name__ == "__main__":
    unittest.main()
