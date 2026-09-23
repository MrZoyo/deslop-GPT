def save_package(path, data):
    path.write_bytes(data)


write_package = save_package


def load_package(path):
    return path.read_bytes()
