import json
import tempfile
import unittest
from pathlib import Path

from app import load_report


class ReportTests(unittest.TestCase):
    def test_loads_available_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.json").write_text(json.dumps({"status": "ok"}))
            (root / "preview.txt").write_text("frame 1")
            descriptor = {"report": "report.json", "optional_preview": "preview.txt"}
            self.assertEqual(load_report(root, descriptor), ({"status": "ok"}, "frame 1"))


if __name__ == "__main__":
    unittest.main()
