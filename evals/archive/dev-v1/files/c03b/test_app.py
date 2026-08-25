import tempfile
import unittest
from pathlib import Path

from app import convert_to_v3


class VersionBridgeTests(unittest.TestCase):
    def test_runs_both_format_stages_and_cleans_intermediate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.write_text("raw")
            seen: list[tuple[str, Path]] = []

            def to_v2(_source: Path, intermediate: Path) -> None:
                intermediate.mkdir()
                (intermediate / "data").write_text("v2")
                seen.append(("v2", intermediate))

            def to_v3(intermediate: Path, target: Path) -> None:
                target.write_text((intermediate / "data").read_text() + "->v3")
                seen.append(("v3", intermediate))

            convert_to_v3(source, output, to_v2, to_v3)
            self.assertEqual(output.read_text(), "v2->v3")
            self.assertEqual([stage for stage, _ in seen], ["v2", "v3"])
            self.assertFalse(seen[0][1].exists())


if __name__ == "__main__":
    unittest.main()
