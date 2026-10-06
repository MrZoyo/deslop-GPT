import hashlib
import json
from pathlib import Path


def write_report(path: Path, records: list[dict]) -> None:
    path.write_text(json.dumps({"records": records, "format": 2}, indent=2))


def read_report(path: Path, expected_sha256: str) -> list[dict]:
    document = json.loads(path.read_text())
    version = document["format"]
    if version == 1:
        records = document["rows"]
    elif version == 2:
        records = document["records"]
    else:
        raise ValueError("unsupported report format")
    if hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != expected_sha256:
        raise ValueError("report corruption")
    return records
