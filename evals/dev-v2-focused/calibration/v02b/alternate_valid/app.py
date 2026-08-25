import hashlib
from pathlib import Path


def write_package(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def load_package(path: Path, manifest: dict[str, object]) -> bytes:
    data = path.read_bytes()
    digest = hashlib.new("sha256", data).hexdigest()
    if digest != manifest["sha256"] or len(data) != manifest["size"]:
        raise ValueError("package manifest mismatch")
    return data
