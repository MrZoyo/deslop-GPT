def _normalize_label(value: str) -> str:
    return " ".join(value.split()).lower()


def public_label(value: str) -> str:
    return _normalize_label(value)
