from pathlib import Path

from core import load_episode as _load_episode


def load_episode(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Stable import path used by external conversion callers."""
    return _load_episode(path)
