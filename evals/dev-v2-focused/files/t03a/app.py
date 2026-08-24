def normalize_identifier(value: str) -> str:
    return value.strip().lower().replace(" ", "-")
