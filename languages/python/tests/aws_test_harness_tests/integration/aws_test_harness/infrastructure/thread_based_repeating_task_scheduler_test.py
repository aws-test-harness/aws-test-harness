from logging import Logger
from time import sleep
from typing import cast, Generator
from unittest.mock import Mock

import pytest

from aws_test_harness.infrastructure.thread_based_repeating_task_scheduler import ThreadBasedRepeatingTaskScheduler
from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching


@pytest.fixture(scope='function')
def repeating_task_scheduler(logger: Logger) -> Generator[ThreadBasedRepeatingTaskScheduler]:
    repeating_task_scheduler = ThreadBasedRepeatingTaskScheduler(logger)

    yield repeating_task_scheduler

    repeating_task_scheduler.reset_schedule()


def test_executes_scheduled_task(repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()

    repeating_task_scheduler.schedule(task)

    wait_for_value_matching(
        lambda: task,
        'task mock to have been called',
        lambda the_task: cast(Mock, the_task).called
    )


def test_repeatedly_executes_scheduled_task(repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()

    repeating_task_scheduler.schedule(task)

    wait_for_value_matching(
        lambda: task,
        'task mock to have been called more than twice',
        lambda the_task: cast(Mock, the_task).call_count > 2
    )


def test_throws_exception_if_asked_to_schedule_task_when_one_is_already_scheduled(
        repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task1 = Mock()
    task2 = Mock()

    repeating_task_scheduler.schedule(task1)

    with pytest.raises(RuntimeError, match='Task is already scheduled'):
        repeating_task_scheduler.schedule(task2)

    wait_for_value_matching(
        lambda: task1,
        'task mock to have been called',
        lambda the_task: cast(Mock, the_task).called
    )

    task2.assert_not_called()


def test_stops_scheduling_task_when_instructed(repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()

    repeating_task_scheduler.schedule(task)

    wait_for_value_matching(
        lambda: task,
        'task mock to have been called',
        lambda the_task: cast(Mock, the_task).called
    )

    repeating_task_scheduler.reset_schedule()

    # Assume that 50ms is enough time for the final invocation of the task to complete
    sleep(0.05)
    task_call_count_snapshot = task.call_count

    # Wait another 50ms to give the task a chance to run again (if the stop feature is broken)
    sleep(0.05)
    assert task.call_count == task_call_count_snapshot


def test_does_not_throw_exception_if_asked_to_reset_schedule_before_a_task_is_scheduled(
        repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    repeating_task_scheduler.reset_schedule()


def test_can_schedule_again_after_resetting_schedule(
        repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    first_task = Mock()

    repeating_task_scheduler.schedule(first_task)

    wait_for_value_matching(
        lambda: first_task,
        'first task mock to have been called',
        lambda the_task: cast(Mock, the_task).called
    )

    repeating_task_scheduler.reset_schedule()

    second_task = Mock()
    repeating_task_scheduler.schedule(second_task)

    wait_for_value_matching(
        lambda: second_task,
        'second task mock to have been called',
        lambda the_task: cast(Mock, the_task).call_count > 0
    )


def test_continues_scheduling_task_after_task_throws_exception(
        repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()

    def task_side_effect() -> int:
        if task.call_count == 0:
            raise Exception('Simulated exception')

        return 1

    task.side_effect = task_side_effect

    repeating_task_scheduler.schedule(task)

    wait_for_value_matching(
        lambda: task,
        'task mock to have been called multiple times',
        lambda the_task: cast(Mock, the_task).call_count > 1
    )


def test_indicates_that_a_task_has_been_scheduled(repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()
    assert repeating_task_scheduler.scheduled() is False

    repeating_task_scheduler.schedule(task)

    assert repeating_task_scheduler.scheduled() is True


def test_indicates_that_a_task_has_not_been_scheduled_after_resetting_schedule(
        repeating_task_scheduler: ThreadBasedRepeatingTaskScheduler) -> None:
    task = Mock()
    repeating_task_scheduler.schedule(task)
    assert repeating_task_scheduler.scheduled() is True

    repeating_task_scheduler.reset_schedule()

    # Assume that 50ms is enough time for the final invocation of the task to complete
    sleep(0.05)
    assert repeating_task_scheduler.scheduled() is False
