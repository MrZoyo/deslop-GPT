from dataclasses import dataclass


DEFAULT_MOTION_THRESHOLD = 1e-3


@dataclass(frozen=True)
class ConversionOptions:
    motion_threshold: float = DEFAULT_MOTION_THRESHOLD
    frame_size: tuple[int, int] = (640, 352)
    rgb_processing: str = "upstream-rectified"


def validate_base_options(options: ConversionOptions) -> None:
    if options.motion_threshold < 0:
        raise ValueError("motion threshold must be non-negative")


def validate_camera_adapter(options: ConversionOptions) -> None:
    validate_base_options(options)
    if options.frame_size != (640, 352):
        raise ValueError("camera adapter requires 640x352 frames")
    if options.rgb_processing != "upstream-rectified":
        raise ValueError("camera adapter requires upstream-rectified RGB")
