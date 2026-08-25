import hashlib
import json
from pathlib import Path


def write_media(root: Path, frames: list[bytes]) -> tuple[Path, Path]:
    media_path = root / "camera.bin"
    payload = b"".join(frames)
    media_path.write_bytes(payload)
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "frame_count": len(frames),
                "media_bytes": len(payload),
                "media_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    )
    return media_path, manifest_path


def validate_persisted_media(media_path: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    payload = media_path.read_bytes()
    if len(payload) != manifest["media_bytes"]:
        raise ValueError("persisted media size mismatch")
    if hashlib.sha256(payload).hexdigest() != manifest["media_sha256"]:
        raise ValueError("persisted media checksum mismatch")
    if manifest["frame_count"] < 1:
        raise ValueError("persisted media contains no frames")
