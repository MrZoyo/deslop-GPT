import json
from pathlib import Path
from typing import Callable


def load_items(text: str) -> list[object]:
    return list(json.loads(text)["items"])


def load_versioned(payload: dict[str, object]) -> list[object]:
    if payload.get("version") == 2:
        return list(payload["items"])
    if payload.get("version") == 1:
        return list(payload["records"])
    raise ValueError("unsupported version")


def write_atomically(path: Path, value: object, encode: Callable[[object], bytes]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_bytes(encode(value))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
