from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDefinition:
    component_package: str


def parse_task(mapping):
    return TaskDefinition(component_package=mapping["component_package"])
