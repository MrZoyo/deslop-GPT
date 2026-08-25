import hashlib
import json


SENSITIVE_TOKENS = ("token", "secret", "password", "api_key")


def sanitize_metadata(records: object) -> dict[str, dict[str, str]]:
    """Prepare independently recorded metadata for a public conversion report."""
    if not isinstance(records, dict):
        return {}
    sanitized: dict[str, dict[str, str]] = {}
    for name, values in records.items():
        if not isinstance(values, dict):
            continue
        safe: dict[str, str] = {}
        for key, value in values.items():
            key_text = str(key)
            value_text = str(value)
            if key_text == "config_text":
                existing = values.get("config_sha256")
                if value_text == "<omitted>" and isinstance(existing, str):
                    digest = existing
                else:
                    digest = hashlib.sha256(value_text.encode()).hexdigest()
                safe["config_sha256"] = digest
                safe[key_text] = "<omitted>"
            elif any(token in key_text.lower() for token in SENSITIVE_TOKENS):
                safe[key_text] = "<redacted>"
            else:
                safe[key_text] = value_text
        sanitized[str(name)] = safe
    return sanitized


def public_report(records: object) -> str:
    return json.dumps(sanitize_metadata(records), sort_keys=True)
