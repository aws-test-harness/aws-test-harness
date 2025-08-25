from dataclasses import dataclass


@dataclass(frozen=True)
class TaskContext:
    command_args: list[str]
    environment_variables: dict[str, str]
