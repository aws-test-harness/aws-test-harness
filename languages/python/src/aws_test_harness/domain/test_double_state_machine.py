from typing import Any, Callable, Dict, Optional, cast
from unittest.mock import Mock

from aws_test_harness.domain.invocation import Invocation

type StateMachineExecutionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


class TestDoubleStateMachine:
    def __init__(self, execution_handler: Optional[StateMachineExecutionHandler] = None):
        self.__mock = Mock()
        self.__mock.side_effect = execution_handler if execution_handler else lambda _: dict()

    def get_result_for(self, invocation: Invocation) -> Dict[str, Any]:
        return cast(Dict[str, Any], self.__mock(invocation.parameters['input']))

    @property
    def call_count(self) -> int:
        return self.__mock.call_count

    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
        self.__mock.assert_called_once_with(*args, **kwargs)
