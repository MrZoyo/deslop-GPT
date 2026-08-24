import json
from pathlib import Path


def publish_records(records: list[dict[str, object]], destination: Path) -> Path:
    destination.write_text(json.dumps(records, sort_keys=True))
    return destination
