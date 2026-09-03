CURRENT_SCHEMA = "2.0"


def migrate_episode(payload):
    if payload.get("schema") != CURRENT_SCHEMA:
        raise ValueError("unsupported migration source")
    return {"schema": CURRENT_SCHEMA, "frames": list(payload["frames"])}
