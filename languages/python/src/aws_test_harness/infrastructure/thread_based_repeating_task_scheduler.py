from logging import Logger
from threading import Thread, Event
from typing import Optional, Callable, Any

from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler


class ThreadBasedRepeatingTaskScheduler(RepeatingTaskScheduler):
    __thread: Optional[Thread] = None

    def __init__(self, logger: Logger):
        self.__logger = logger
        self.__reset_schedule_event = Event()

    def schedule(self, task: Callable[..., Any]) -> None:
        if self.__thread is not None:
            raise RuntimeError('Task is already scheduled')

        def repeat_task_until_signalled() -> None:
            while not self.__reset_schedule_event.is_set():
                try:
                    task()
                except BaseException as e:
                    self.__logger.exception('Uncaught exception in thread-based repeating task scheduler thread',
                                            exc_info=e)

        self.__logger.debug('Starting repeating task scheduler thread...')
        self.__thread = Thread(target=repeat_task_until_signalled, daemon=True)
        self.__thread.start()
        self.__logger.debug('Repeating task scheduler thread started.')

    def scheduled(self) -> bool:
        return self.__thread is not None

    def reset_schedule(self) -> None:
        self.__logger.debug('Signalling repeating task schedule should reset...')
        self.__reset_schedule_event.set()

        if self.__thread:
            self.__thread.join()
            self.__thread = None

        self.__logger.debug('Repeating task schedule reset.')

        self.__reset_schedule_event.clear()
