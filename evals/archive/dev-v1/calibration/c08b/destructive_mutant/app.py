def verify_episode(
    events: list[str],
    *,
    final_angle: float,
    target_angle: float,
    numeric_ok: bool,
    rebound: float,
    rebound_limit: float,
) -> bool:
    if final_angle < target_angle:
        raise ValueError("episode did not reach the target")
    return True
