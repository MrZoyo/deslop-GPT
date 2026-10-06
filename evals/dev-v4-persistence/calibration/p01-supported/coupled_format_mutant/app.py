import hashlib
import json


def write_report(path, records):
    path.write_text(json.dumps(records))


def read_report(path, expected_sha256):
    records = json.loads(path.read_text())
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("report corruption")
    return records
