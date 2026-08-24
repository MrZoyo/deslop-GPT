import hashlib
from pathlib import Path


def write_package(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def load_package(path: Path, manifest: dict[str, object]) -> bytes:
    data = path.read_bytes()
    if len(data) != manifest["size"]:
        raise ValueError("package size mismatch")
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("package digest mismatch")
    return data
