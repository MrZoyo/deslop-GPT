def read_actions(record: dict[str, object]) -> list[float]:
    """Read the current field or the documented legacy field."""
    try:
        values = record["action"]
    except KeyError:
        values = record["actions"]
    if not isinstance(values, list):
        raise TypeError("action field must be a list")
    return [float(value) for value in values]
