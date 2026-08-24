import hashlib
import json


def calibration_digest(calibration: dict[str, object]) -> str:
    payload = json.dumps(calibration, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def scan_calibrations(
    episodes: list[tuple[str, dict[str, object]]],
) -> dict[str, object]:
    variants = [
        {"episode_id": episode_id, "sha256": calibration_digest(calibration)}
        for episode_id, calibration in episodes
    ]
    return {"canonical_sha256": variants[0]["sha256"], "episodes": variants}
