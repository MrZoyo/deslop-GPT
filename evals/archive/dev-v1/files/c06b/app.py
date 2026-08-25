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
    formats = {message.encoded_format for message in messages}
    if "" in formats or len(formats) != 1:
        raise ValueError("video format must be non-empty and consistent")

    selected: list[int] = []
    for output_time in output_times_ms:
        nearest = min(messages, key=lambda item: abs(item.timestamp_ms - output_time))
        if abs(nearest.timestamp_ms - output_time) > max_fill_gap_ms:
            raise ValueError("nearest source frame exceeds the video fill-gap limit")
        selected.append(nearest.source_index)
    return selected
