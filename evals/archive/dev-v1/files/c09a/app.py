import json


def pack_samples(frames: list[int], full_action: list[float]) -> tuple[bytes, list[dict[str, int]]]:
    payload = json.dumps(full_action, separators=(",", ":")).encode() + b"\n"
    blob = bytearray()
    records: list[dict[str, int]] = []
    for frame_index in frames:
        offset = len(blob)
        blob.extend(payload)
        records.append(
            {
                "frame_index": frame_index,
                "full_action_anchor_index": frame_index,
                "full_action_offset": offset,
                "full_action_size": len(payload),
            }
        )
    return bytes(blob), records


def read_full_action(blob: bytes, record: dict[str, int]) -> list[float]:
    start = record["full_action_offset"]
    end = start + record["full_action_size"]
    return json.loads(blob[start:end])
