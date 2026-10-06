import hashlib
import json
from pathlib import Path


def _canonical(records):
    return json.dumps(records, sort_keys=True, separators=(",", ":")).encode()


def _local_receipt(records):
    payload = _canonical(records)
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def _receipt_matches(records, receipt):
    return receipt == _local_receipt(records)


def write_report(path: Path, records: list[dict]) -> None:
    receipt = _local_receipt(records)
    if not _receipt_matches(records, receipt):
        raise ValueError("local receipt mismatch")
    path.write_text(json.dumps({"format": 2, "records": records, "receipt": receipt}))


def read_report(path: Path, expected_sha256: str) -> list[dict]:
    document = json.loads(path.read_text())
    version = document["format"]
    if version == 1:
        records = document["rows"]
    elif version == 2:
        records = document["records"]
    else:
        raise ValueError("unsupported report format")
    if hashlib.sha256(_canonical(records)).hexdigest() != expected_sha256:
        raise ValueError("report corruption")
    return records
