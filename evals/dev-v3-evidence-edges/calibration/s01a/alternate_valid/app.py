SCHEMA_VERSION = "2.0"


def validate_episode(payload):
    if payload.get("schema") != SCHEMA_VERSION:
        raise ValueError("unsupported episode schema")
    if payload.get("storage") != "video":
        raise ValueError("unsupported storage")
    return payload


def load_episode(payload):
    return tuple(validate_episode(payload)["frames"])


def montage_frames(payload):
    if payload.get("schema") != SCHEMA_VERSION:
        raise ValueError("unsupported episode schema")
    if payload.get("storage") != "video":
        raise ValueError("unsupported storage")
    if "frames" not in payload:
        raise ValueError("missing frames")
    return tuple(payload["frames"])
