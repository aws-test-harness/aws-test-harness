from time import time
from typing import Callable, Optional


def wait_for_value_matching[T](try_get_value: Callable[[], Optional[T]], value_description: str,
                               predicate: Callable[[Optional[T]], bool],
                               timeout_millis: int = 5 * 1000) -> Optional[T]:
    milliseconds_since_epoch = get_epoch_milliseconds()

    expiry_time = milliseconds_since_epoch + timeout_millis

    value: Optional[T] = None
    last_non_none_value: Optional[T] = None

    condition_satisfied = False

    while not condition_satisfied and get_epoch_milliseconds() < expiry_time:
        value = try_get_value()

        if value is not None:
            last_non_none_value = value

        # noinspection PyBroadException
        try:
            condition_satisfied = predicate(value)
        except BaseException:
            pass

    assert condition_satisfied, (
            f'Timed out waiting for {value_description}' +
            (
                f'\n\nLatest retrieved value was {value}'
                if value is not None else (
                    '\n\nValue retrieved was None at all times'
                    if last_non_none_value is None
                    else f'\n\nLatest retrieved value was None but previously it was {last_non_none_value}'
                ))
    )

    return value


def get_epoch_milliseconds() -> int:
    return int(round(time() * 1000))
