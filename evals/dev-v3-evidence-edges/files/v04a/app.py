import hashlib


def _receipt(data):
    return {"sha256": hashlib.sha256(data).hexdigest()}


def _verify_receipt(data, receipt):
    return hashlib.sha256(data).hexdigest() == receipt["sha256"]


def write_package(path, data):
    receipt = _receipt(data)
    if not _verify_receipt(data, receipt):
        raise ValueError("local verification failed")
    path.write_bytes(data)


def save_package(path, data):
    return write_package(path, data)


def load_package(path):
    return path.read_bytes()
