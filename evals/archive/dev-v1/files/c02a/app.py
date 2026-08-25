from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EpisodeResult:
    output_path: Path | None


def completed_results(root: Path) -> list[EpisodeResult]:
    outputs = [root / "episode-0", root / "episode-1"]
    for path in outputs:
        path.mkdir()
    return [EpisodeResult(path) for path in outputs]
