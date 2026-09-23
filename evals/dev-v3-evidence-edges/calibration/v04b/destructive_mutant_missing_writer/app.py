import hashlib


def load_package(path, manifest):
    data = path.read_bytes()
    if len(data) != manifest["size"]:
        raise ValueError("package size mismatch")
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("package digest mismatch")
    return data
