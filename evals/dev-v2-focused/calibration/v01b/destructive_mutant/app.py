from pathlib import Path


def write_artifact(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def verify_artifact(path: Path, expected_sha256: str) -> bytes:
    return path.read_bytes()
