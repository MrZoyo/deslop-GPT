def decode_frame(
    payload: bytes,
    *,
    encoded_format: str,
    decoded_size: tuple[int, int],
    rotate: bool,
) -> bytes:
    """Decode a frame from an independently produced recording."""
    if encoded_format not in {"h264", "hevc"}:
        raise ValueError("unsupported or missing encoded format")
    if decoded_size != (640, 352):
        raise ValueError("decoded frame does not match the calibrated pixel space")
    return payload[::-1] if rotate else payload
