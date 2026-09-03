import json
import tempfile
import unittest
from pathlib import Path

from app import build_assets


ROOT = Path(__file__).parent


class AssetCompilerTests(unittest.TestCase):
    def test_compiles_representative_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "source": str(ROOT / "source.json"),
                        "output": str(Path(directory) / "compiled.json"),
                    }
                )
            )
            self.assertEqual(
                build_assets(config_path),
                {"joint": "hinge", "collision": "door-panel"},
            )


if __name__ == "__main__":
    unittest.main()
