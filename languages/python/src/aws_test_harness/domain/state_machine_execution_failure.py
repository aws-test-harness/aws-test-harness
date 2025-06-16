from dataclasses import dataclass


@dataclass(frozen=True)
class StateMachineExecutionFailure:
    cause: str
    error: str
