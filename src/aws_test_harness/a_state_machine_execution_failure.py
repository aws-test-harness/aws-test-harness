from dataclasses import dataclass


@dataclass
class AStateMachineExecutionFailure:
    error: str
    cause: str


def a_state_machine_execution_failure(error: str, cause: str) -> AStateMachineExecutionFailure:
    return AStateMachineExecutionFailure(error, cause)
