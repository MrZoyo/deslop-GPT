CURRENT_TASK_ID = "TASK-CURRENT-03"


def build_current_package(task_id):
    return {"schema": "current-1", "task_id": task_id, "target_degrees": 5}


def load_current_package(package):
    if package["schema"] != "current-1":
        raise ValueError("unsupported package schema")
    return package["task_id"], package["target_degrees"]


class OpenDoorStateMachine:
    def __init__(self, task_id, target_degrees):
        self.task_id = task_id
        self.target_degrees = target_degrees

    def run(self):
        return self.task_id == CURRENT_TASK_ID and self.target_degrees == 5


def run_current_episode(task_id):
    loaded = load_current_package(build_current_package(task_id))
    return OpenDoorStateMachine(*loaded).run()
