from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory


def convert_to_v3(
    source: Path,
    output: Path,
    convert_to_v2: Callable[[Path, Path], None],
    upgrade_v2_to_v3: Callable[[Path, Path], None],
) -> None:
    """Bridge two independently versioned dataset formats."""
    with TemporaryDirectory(prefix="v2-intermediate-") as directory:
        intermediate = Path(directory) / "dataset-v2"
        convert_to_v2(source, intermediate)
        upgrade_v2_to_v3(intermediate, output)
