from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler


# TODO: Retrofit tests
class InvocationListener:
    def __init__(self, invocation_handler: InvocationHandler, repeating_task_scheduler: RepeatingTaskScheduler):
        self.__invocation_handler = invocation_handler
        self.__repeating_task_scheduler = repeating_task_scheduler

    def ensure_started(self) -> None:
        if not self.__repeating_task_scheduler.scheduled():
            self.__repeating_task_scheduler.schedule(self.__invocation_handler.handle_pending_invocation)

    def stop(self) -> None:
        self.__repeating_task_scheduler.reset_schedule()
