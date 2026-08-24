import json


def load_items(text: str) -> list[object]:
    return json.loads(text)["items"]
