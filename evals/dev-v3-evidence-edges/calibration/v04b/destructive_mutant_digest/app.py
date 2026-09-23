import hashlib


def write_package(path, data):
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


save_package = write_package


def load_package(path, manifest):
    data = path.read_bytes()
    if len(data) != manifest["size"]:
        raise ValueError("package size mismatch")
    return data
