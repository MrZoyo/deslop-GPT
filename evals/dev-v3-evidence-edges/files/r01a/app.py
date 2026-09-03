def active_camera():
    return {"name": "front", "parent": "head"}


def camera_from_config(config):
    if config.get("future_left", False):
        return {"name": "left", "parent": "left_wrist"}
    return active_camera()
