from dataclasses import dataclass

from domain.task_context import TaskContext


@dataclass(frozen=True)
class Invocation:
    task_definition_arn: str
    task_family: str
    container_name: str
    id: str
    mocking_session_id: str
    task_context: TaskContext
