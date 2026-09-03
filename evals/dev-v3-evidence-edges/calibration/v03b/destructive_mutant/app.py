import json


def load_report(root, descriptor):
    report = json.loads((root / descriptor["report"]).read_text())
    preview = (root / descriptor["optional_preview"]).read_text()
    return report, preview
