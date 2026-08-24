import json
from pathlib import Path
from typing import Callable


def _validate_items(items: object) -> list[object]:
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    return items


def _parse_current(text: str) -> list[object]:
    return _validate_items(json.loads(text)["items"])


def _parse_legacy(text: str) -> list[object]:
    return [line for line in text.splitlines() if line]


def load_items(text: str) -> list[object]:
    try:
        return _parse_current(text)
    except Exception as error:
        if isinstance(error, KeyError):
            return _parse_legacy(text)
        raise


def load_versioned(payload: dict[str, object]) -> list[object]:
    if payload.get("version") == 2:
        return _validate_items(payload["items"])
    if payload.get("version") == 1:
        return _validate_items(payload["records"])
    raise ValueError("unsupported version")


def write_atomically(path: Path, value: object, encode: Callable[[object], bytes]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_bytes(encode(value))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
