from abc import ABCMeta, abstractmethod
from copy import deepcopy
from typing import Any, List, Callable

from aws_test_harness.domain.invocation import Invocation


class InvocationTargetTwin(metaclass=ABCMeta):

    def __init__(self, invocation_handler: Callable[..., Any]) -> None:
        self.__invocation_handler = invocation_handler
        self.__invocation_count = 0
        self.__invocations: List[List[Any]] = []

    def get_result_for(self, invocation: Invocation) -> Any:
        # TODO: Ensure threadsafe
        self.__invocation_count += 1
        invocation_args = self._get_invocation_args(invocation)
        self.__invocations.append(invocation_args)
        return dict(value=self.__invocation_handler(*invocation_args))

    @property
    def invocation_count(self) -> int:
        return self.__invocation_count

    @property
    def invocations(self) -> List[List[Any]]:
        return deepcopy(self.__invocations)

    def _set_invocation_handler(self, invocation_handler: Callable[..., Any]) -> None:
        self.__invocation_handler = invocation_handler

    @abstractmethod
    def _get_invocation_args(self, invocation: Invocation) -> List[Any]:
        pass
