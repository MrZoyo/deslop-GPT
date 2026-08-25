def transform_frame(
    pixels: tuple[int, ...],
    *,
    rotate: bool,
    recorded_at: object | None = None,
) -> tuple[int, ...]:
    return tuple(reversed(pixels)) if rotate else pixels
