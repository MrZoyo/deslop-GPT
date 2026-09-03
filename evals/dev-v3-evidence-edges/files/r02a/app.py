def summarize_current(values):
    return {"count": len(values), "total": sum(values)}


def load_legacy_package(package):
    return package["legacy_task_id"]


def run_legacy_episode(package):
    return load_legacy_package(package) == "retired-task"
