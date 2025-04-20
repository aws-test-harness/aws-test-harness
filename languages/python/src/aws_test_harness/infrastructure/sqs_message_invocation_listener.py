from logging import Logger
from typing import Callable

from aws_test_harness.domain.invocation_listener import InvocationListener
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.infrastructure.thread_based_repeating_task_scheduler import ThreadBasedRepeatingTaskScheduler


class SqsMessageInvocationListener(InvocationListener):
    def __init__(self, invocation_post_office: InvocationPostOffice, logger: Logger):
        self.__invocation_post_office = invocation_post_office
        self.__repeating_background_task = ThreadBasedRepeatingTaskScheduler(logger)

    def listen(self, handle_invocation: Callable[[str, str], None]) -> None:
        def task() -> None:
            invocation = self.__invocation_post_office.maybe_collect_invocation()

            if invocation:
                handle_invocation(invocation.target, invocation.id)

        self.__repeating_background_task.schedule(task)

    def stop(self):
        self.__repeating_background_task.reset_schedule()
