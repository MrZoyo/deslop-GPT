import hashlib
import json
from pathlib import Path


def write_report(path: Path, records: list[dict[str, object]]) -> dict[str, object]:
    path.write_text(json.dumps({"records": records}, sort_keys=True))
    return {"records": records}


def read_persisted_report(path: Path, expected_sha256: str) -> list[dict[str, object]]:
    report = json.loads(path.read_text())
    payload = json.dumps(report["records"], sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("persisted report corruption")
    return list(report["records"])
