from pathlib import Path
from typing import Callable


def write_atomically(path: Path, value: object, encode: Callable[[object], bytes]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_bytes(encode(value))
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
