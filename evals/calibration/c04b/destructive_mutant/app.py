def read_actions(record: dict[str, object]) -> list[float]:
    values = record["action"]
    if not isinstance(values, list):
        raise TypeError("action field must be a list")
    return [float(value) for value in values]
