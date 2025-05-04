from abc import ABCMeta, abstractmethod

from test_double_invocation_handler_code.domain.invocation import Invocation
from test_double_invocation_handler_code.domain.retrieval_attempt import RetrievalAttempt


class InvocationPostOffice(metaclass=ABCMeta):
    @abstractmethod
    def post_invocation(self, invocation: Invocation) -> None:
        pass

    @abstractmethod
    def maybe_collect_result(self, invocation: Invocation) -> RetrievalAttempt:
        pass
