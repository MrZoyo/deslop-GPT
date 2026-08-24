import hashlib
import json


def build_report(records: list[dict[str, object]]) -> dict[str, object]:
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return {"records": records, "checksum": hashlib.sha256(payload).hexdigest()}


def validate_report(report: dict[str, object]) -> bool:
    payload = json.dumps(report["records"], sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest() == report["checksum"]
