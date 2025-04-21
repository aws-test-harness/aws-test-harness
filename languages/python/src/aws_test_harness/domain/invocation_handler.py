from typing import Callable, Any

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice


class InvocationHandler:
    def __init__(self, invocation_post_office: InvocationPostOffice,
                 get_invocation_result: Callable[[Invocation], Any]):
        self.__invocation_post_office = invocation_post_office
        self.__get_invocation_result = get_invocation_result

    def handle_pending_invocation(self) -> None:
        invocation = self.__invocation_post_office.maybe_collect_invocation()

        if invocation:
            self.__invocation_post_office.post_result(
                invocation.id,
                dict(value=self.__get_invocation_result(invocation))
            )
