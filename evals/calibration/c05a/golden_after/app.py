def transform_frame(
    pixels: tuple[int, ...],
    *,
    rotate: bool,
) -> tuple[int, ...]:
    return tuple(reversed(pixels)) if rotate else pixels
