from dataclasses import dataclass
from typing import Optional


@dataclass
class StateMachineExecutionResult:
    status: str
    output: Optional[str]
    error: Optional[str]
    cause: Optional[str]
