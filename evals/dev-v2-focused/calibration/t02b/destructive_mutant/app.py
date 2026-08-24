def parse_header(payload: dict[str, object]) -> str:
    if "header" in payload:
        return str(payload["header"])
    raise KeyError("header")
