import hashlib
import json
from pathlib import Path


def first_record(path: Path, record_type: str) -> dict[str, object] | None:
    for line in path.read_text().splitlines():
        record = json.loads(line)
        if record.get("type") == record_type:
            return record
    return None


def json_equal_via_digest(left: object, right: object) -> bool:
    def digest(value: object) -> str:
        payload = json.dumps(value, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    return digest(left) == digest(right)


def load_episode(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return records[0], records[-1]
