from datetime import datetime


ROTATION_CUTOFF = datetime.fromisoformat("2026-01-15T00:00:00")


def transform_frame(
    pixels: tuple[int, ...],
    *,
    rotate: bool | None = None,
    recorded_at: datetime | None = None,
) -> tuple[int, ...]:
    if rotate is None:
        rotate = recorded_at is not None and recorded_at < ROTATION_CUTOFF
    return tuple(reversed(pixels)) if rotate else pixels
