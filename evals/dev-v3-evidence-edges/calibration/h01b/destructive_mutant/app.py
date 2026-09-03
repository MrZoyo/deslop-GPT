import json


def load_protocol_fixture(path):
    payload = json.loads(path.read_text())
    return tuple(payload["channels"])
