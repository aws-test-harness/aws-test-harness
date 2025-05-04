from time import sleep
from typing import Any

from test_double_invocation_handler.domain.invocation import Invocation
from test_double_invocation_handler.domain.invocation_post_office import InvocationPostOffice


class InvocationResultService:

    def __init__(self, invocation_post_office: InvocationPostOffice):
        self.__invocation_post_office = invocation_post_office

    def generate_result_for(self, invocation: Invocation) -> Any:
        self.__invocation_post_office.post_invocation(invocation)
        # TODO: Poll rather than sleep
        sleep(1)
        # TODO: Support result value of 'None'
        return self.__invocation_post_office.maybe_collect_result(invocation)
