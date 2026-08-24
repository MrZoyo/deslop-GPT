from pathlib import Path


def write_package(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def load_package(path: Path, manifest: dict[str, object]) -> bytes:
    return path.read_bytes()
