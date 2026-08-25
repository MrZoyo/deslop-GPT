import hashlib


SENSITIVE_TOKENS = ("token", "secret", "password", "api_key")


def sanitize_metadata(records: object) -> dict[str, dict[str, str]]:
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
                safe["config_sha256"] = hashlib.sha256(value_text.encode()).hexdigest()
                safe[key_text] = "<omitted>"
            elif any(token in key_text.lower() for token in SENSITIVE_TOKENS):
                safe[key_text] = "<redacted>"
            else:
                safe[key_text] = value_text
        sanitized[str(name)] = safe
    return sanitized
