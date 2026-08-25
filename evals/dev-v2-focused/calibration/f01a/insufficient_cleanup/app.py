import json


def parse_current(text: str) -> list[object]:
    return json.loads(text)["items"]


def parse_legacy(text: str) -> list[object]:
    return [line for line in text.splitlines() if line]


def load_items(text: str) -> list[object]:
    payload = json.loads(text)
    if "items" in payload:
        return payload["items"]
    return parse_legacy(text)
