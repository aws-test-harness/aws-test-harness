from dataclasses import dataclass


@dataclass
class ExitCode:
    value: int


def an_exit_code(value: int) -> ExitCode:
    return ExitCode(value)
