REQUIRED_EVENT_ORDER = ("release", "clearance", "target", "settle")


def verify_episode(
    events: list[str],
    *,
    final_angle: float,
    target_angle: float,
    numeric_ok: bool,
    rebound: float,
    rebound_limit: float,
) -> bool:
    positions = []
    for required in REQUIRED_EVENT_ORDER:
        try:
            positions.append(events.index(required))
        except ValueError as error:
            raise ValueError(f"missing required event: {required}") from error
    if positions != sorted(positions):
        raise ValueError("episode events violate the required physical order")
    if not numeric_ok:
        raise ValueError("episode contains an invalid numerical state")
    if final_angle < target_angle:
        raise ValueError("episode did not reach the target")
    if rebound > rebound_limit:
        raise ValueError("episode rebounded after reaching the target")
    return True
