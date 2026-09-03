import json


def load_protocol_fixture(path):
    payload = json.loads(path.read_text())
    if payload["schema"] != "sensor-protocol-2":
        raise ValueError("unsupported protocol fixture")
    return tuple(payload["channels"])
