from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMessage:
    timestamp_ms: float
    encoded_format: str
    source_index: int


def select_video_frames(
    messages: list[VideoMessage],
    output_times_ms: list[float],
    *,
    max_fill_gap_ms: float,
) -> list[int]:
    if not messages:
        raise ValueError("video stream is empty")
    return [
        min(messages, key=lambda item: abs(item.timestamp_ms - output_time)).source_index
        for output_time in output_times_ms
    ]
