from collections.abc import Callable
from pathlib import Path


def convert_to_v3(
    source: Path,
    output: Path,
    convert_to_v2: Callable[[Path, Path], None],
    upgrade_v2_to_v3: Callable[[Path, Path], None],
) -> None:
    upgrade_v2_to_v3(source, output)
