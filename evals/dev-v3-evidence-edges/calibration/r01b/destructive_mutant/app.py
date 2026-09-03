ACTIVE_CAMERA_CONFIGS = {
    "right": {"name": "right", "parent": "right_wrist"},
}


def camera_from_active_config(side):
    return dict(ACTIVE_CAMERA_CONFIGS[side])
