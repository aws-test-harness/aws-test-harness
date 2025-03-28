from time import time
from typing import Callable, Optional


def wait_for_value_matching[T](try_get_value: Callable[[], Optional[T]], value_description: str,
                               predicate: Callable[[T], bool],
                               timeout_millis: int = 5 * 1000) -> T:
    milliseconds_since_epoch = get_epoch_milliseconds()

    expiry_time = milliseconds_since_epoch + timeout_millis

    value: Optional[T] = None

    condition_satisfied = False

    while not condition_satisfied and get_epoch_milliseconds() < expiry_time:
        value = try_get_value()

        # noinspection PyBroadException
        try:
            condition_satisfied = predicate(value)
        except BaseException:
            pass

    assert condition_satisfied, f'Timed out waiting for {value_description}. Latest retrieved value was {value}'

    return value


def get_epoch_milliseconds() -> int:
    return int(round(time() * 1000))
