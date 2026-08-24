import json


def render_user(name: str) -> str:
    return f"User: {name}"


def export_wire_user(name: str) -> bytes:
    return json.dumps({"display": render_user(name)}).encode()
