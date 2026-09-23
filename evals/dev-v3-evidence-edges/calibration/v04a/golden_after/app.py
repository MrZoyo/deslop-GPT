def write_package(path, data):
    path.write_bytes(data)


save_package = write_package


def load_package(path):
    return path.read_bytes()
