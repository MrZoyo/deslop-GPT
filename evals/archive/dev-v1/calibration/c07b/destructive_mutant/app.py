import json


def sanitize_metadata(records: object) -> dict[str, object]:
    return records if isinstance(records, dict) else {}


def public_report(records: object) -> str:
    return json.dumps(sanitize_metadata(records), sort_keys=True)
