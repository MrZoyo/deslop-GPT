import hashlib
import json


def verify_artifact(path, expected_sha256):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("artifact digest mismatch")
    return json.loads(data)


def load_package(root, descriptor):
    artifact_path = root / descriptor["artifact"]
    if artifact_path.is_file():
        verify_artifact(artifact_path, descriptor["artifact_sha256"])
    return json.loads((root / "component.json").read_text())
