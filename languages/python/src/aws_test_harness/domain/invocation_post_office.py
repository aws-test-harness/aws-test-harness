from abc import ABCMeta, abstractmethod
from typing import Any, Optional

from aws_test_harness.domain.invocation import Invocation


class InvocationPostOffice(metaclass=ABCMeta):
    @abstractmethod
    def maybe_collect_invocation(self) -> Optional[Invocation]:
        pass

    @abstractmethod
    def post_result(self, invocation_id: str, result: Any) -> None:
        pass
