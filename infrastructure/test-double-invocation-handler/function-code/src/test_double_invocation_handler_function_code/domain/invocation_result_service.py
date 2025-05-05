import time
from typing import Any

from test_double_invocation_handler_messaging.domain.invocation_result_retrieval_timeout_exception import \
    InvocationResultRetrievalTimeoutException
from test_double_invocation_handler_messaging.domain.invocation import Invocation
from test_double_invocation_handler_messaging.domain.invocation_post_office import InvocationPostOffice


class InvocationResultService:

    def __init__(self, invocation_post_office: InvocationPostOffice, timeout_millis: int):
        self.__invocation_post_office = invocation_post_office
        self.__timeout_millis = timeout_millis

    def generate_result_for(self, invocation: Invocation) -> Any:
        self.__invocation_post_office.post_invocation(invocation)

        timeout_time = time.time() * 1000 + self.__timeout_millis

        while True:
            retrieval_attempt = self.__invocation_post_office.maybe_collect_result(invocation)

            if retrieval_attempt.succeeded:
                return retrieval_attempt.value

            if time.time() * 1000 > timeout_time:
                raise InvocationResultRetrievalTimeoutException(
                    f'Timed out after {self.__timeout_millis}ms waiting for result for invocation {invocation.id}'
                )

            time.sleep(0.001)
