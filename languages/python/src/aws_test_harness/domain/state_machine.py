from abc import ABCMeta, abstractmethod
from typing import Dict, Any

from aws_test_harness.domain.state_machine_execution import StateMachineExecution


class StateMachine(metaclass=ABCMeta):
    @abstractmethod
    def execute(self, execution_input: Dict[str, Any]) -> StateMachineExecution:
        pass
