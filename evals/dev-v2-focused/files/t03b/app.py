def normalize_identifier(value: str) -> str:
    if value == "":
        raise ValueError("identifier is empty")
    return value.strip().casefold().replace(" ", "-")
