import hashlib
import json
from pathlib import Path


def _canonical(records):
    return json.dumps(records, sort_keys=True, separators=(",", ":")).encode()


def write_report(path: Path, records: list[dict]) -> None:
    path.write_text(json.dumps({"format": 2, "records": records}))


def read_report(path: Path, expected_sha256: str) -> list[dict]:
    document = json.loads(path.read_text())
    if document["format"] != 2:
        raise ValueError("unsupported report format")
    records = document["records"]
    if hashlib.sha256(_canonical(records)).hexdigest() != expected_sha256:
        raise ValueError("report corruption")
    return records
