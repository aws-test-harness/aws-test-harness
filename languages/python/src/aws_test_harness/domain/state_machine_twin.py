from typing import Any, Callable, Dict, Optional, List

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_target_twin import InvocationTargetTwin

type StateMachineExecutionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class StateMachineTwin(InvocationTargetTwin):

    def __init__(self, execution_handler: Optional[StateMachineExecutionHandler] = None):
        super().__init__(execution_handler if execution_handler else lambda _: dict())

    def _get_invocation_args(self, invocation: Invocation) -> List[Any]:
        return [invocation.parameters['input']]
