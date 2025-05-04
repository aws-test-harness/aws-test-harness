from abc import ABCMeta, abstractmethod
from typing import Any

from test_double_invocation_handler.domain.invocation import Invocation


class InvocationPostOffice(metaclass=ABCMeta):
    @abstractmethod
    def post_invocation(self, invocation: Invocation) -> None:
        pass

    @abstractmethod
    def maybe_collect_result(self, invocation: Invocation) -> Any:
        pass
