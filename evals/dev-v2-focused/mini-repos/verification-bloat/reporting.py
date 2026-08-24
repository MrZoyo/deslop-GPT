import hashlib
import json
from pathlib import Path


def write_report(path: Path, records: list[dict[str, object]]) -> dict[str, object]:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()
    envelope = {"records": records, "sha256": digest}
    path.write_text(json.dumps(envelope, sort_keys=True))
    return {"records": records, "sha256": digest, "receipt": {"bytes": len(payload)}}


def validate_report(report: dict[str, object]) -> bool:
    payload = json.dumps(report["records"], sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest() == report["sha256"]


def read_persisted_report(path: Path, expected_sha256: str) -> list[dict[str, object]]:
    report = json.loads(path.read_text())
    payload = json.dumps(report["records"], sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("persisted report corruption")
    return list(report["records"])
