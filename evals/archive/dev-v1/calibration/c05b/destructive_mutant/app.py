def decode_frame(
    payload: bytes,
    *,
    encoded_format: str,
    decoded_size: tuple[int, int],
    rotate: bool,
) -> bytes:
    return payload[::-1] if rotate else payload
