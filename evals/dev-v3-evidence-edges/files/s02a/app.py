from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDefinition:
    component_package: str = "outputs/old-component-catalog"


def parse_task(mapping):
    return TaskDefinition(
        component_package=mapping.get(
            "component_package",
            "outputs/old-component-catalog",
        )
    )
