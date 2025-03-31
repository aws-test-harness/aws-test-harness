from abc import ABCMeta, abstractmethod
from typing import Any, Dict


class InvocationPostOffice(metaclass=ABCMeta):
    @abstractmethod
    def post_invocation(self, invocation_target: str, invocation_id: str, event: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def maybe_collect_result(self, invocation_id: str) -> Any:
        pass
