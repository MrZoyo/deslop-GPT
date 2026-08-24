import json


def render_user(name: str) -> str:
    return f"User: {name}"


def export_wire_user(name: str) -> bytes:
    return ("USR/1 " + json.dumps({"display": render_user(name)}, sort_keys=True)).encode()
