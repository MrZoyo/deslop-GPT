CURRENT_SCHEMA = "2.0"
LEGACY_SCHEMA = "1.0"


def migrate_episode(payload):
    if payload.get("schema") == LEGACY_SCHEMA:
        return {"schema": CURRENT_SCHEMA, "frames": list(payload["images"])}
    if payload.get("schema") == CURRENT_SCHEMA:
        return {"schema": CURRENT_SCHEMA, "frames": list(payload["frames"])}
    raise ValueError("unsupported migration source")
