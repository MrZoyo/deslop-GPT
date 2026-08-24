def load_items(payload: dict[str, object]) -> list[object]:
    version = payload.get("version")
    if version == 2:
        return list(payload["items"])
    if version == 1:
        return list(payload["records"])
    raise ValueError(f"unsupported version: {version}")
