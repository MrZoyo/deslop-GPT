import json


def parse_current(text: str) -> list[object]:
    return json.loads(text)["items"]


def parse_legacy(text: str) -> list[object]:
    return [line for line in text.splitlines() if line]


def load_items(text: str) -> list[object]:
    try:
        return parse_current(text)
    except Exception:
        if text.startswith("legacy:"):
            return parse_legacy(text.removeprefix("legacy:"))
        raise
