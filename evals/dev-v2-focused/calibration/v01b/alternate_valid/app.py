import hashlib
from pathlib import Path


def write_artifact(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def verify_artifact(path: Path, expected_sha256: str) -> bytes:
    data = path.read_bytes()
    digest = hashlib.new("sha256", data).hexdigest()
    if digest != expected_sha256:
        raise ValueError("artifact digest mismatch")
    return data
