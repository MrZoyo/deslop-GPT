def read_name(value: dict[str, object]) -> str:
    try:
        return str(value["name"])
    except Exception:
        return "unknown"
