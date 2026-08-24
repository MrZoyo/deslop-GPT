from collections.abc import Callable
from pathlib import Path


def publish_episode(root: Path, render: Callable[[], bytes]) -> Path:
    target = root / "episode.bin"
    partial = root / "episode.bin.partial"
    try:
        partial.write_bytes(render())
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return target
