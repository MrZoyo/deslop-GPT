import json
from pathlib import Path


def publish_records(records: list[dict[str, object]], destination: Path) -> Path:
    if not records:
        raise ValueError("at least one record is required")
    destination.write_text(json.dumps(records, sort_keys=True))
    return destination
