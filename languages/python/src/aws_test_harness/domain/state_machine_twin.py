from typing import Any, Callable, Dict, Optional

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_target_twin import InvocationTargetTwin

type StateMachineExecutionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class StateMachineTwin(InvocationTargetTwin):
    def __init__(self, execution_handler: Optional[StateMachineExecutionHandler] = None):
        super().__init__()
        self._mock.side_effect = execution_handler if execution_handler else lambda _: dict()

    def get_result_for(self, invocation: Invocation) -> Any:
        return self._mock(invocation.parameters['input'])
