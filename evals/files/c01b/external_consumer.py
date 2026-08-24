from pathlib import Path

from app import load_episode


def episode_passed(path: Path) -> bool:
    _, result = load_episode(path)
    return result.get("passed") is True
