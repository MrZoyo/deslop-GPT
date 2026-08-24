def parse_header(payload: dict[str, object]) -> str:
    if "header" in payload:
        return str(payload["header"])
    if "legacy_header" in payload:
        return str(payload["legacy_header"])
    raise KeyError("header")
