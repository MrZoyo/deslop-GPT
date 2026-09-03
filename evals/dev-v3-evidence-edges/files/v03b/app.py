import json


def load_report(root, descriptor):
    report = json.loads((root / descriptor["report"]).read_text())
    preview = None
    preview_name = descriptor.get("optional_preview")
    if preview_name is not None:
        preview_path = root / preview_name
        if preview_path.is_file():
            preview = preview_path.read_text()
    return report, preview
