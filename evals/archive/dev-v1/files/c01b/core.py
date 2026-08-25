import json
from pathlib import Path


def load_episode(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return records[0], records[-1]
