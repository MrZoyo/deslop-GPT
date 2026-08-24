from pathlib import Path
from typing import Callable


def write_atomically(path: Path, value: object, encode: Callable[[object], bytes]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(b"partial")
    raise RuntimeError("published partial output")
