from time import time
from typing import Callable, Optional


def wait_for_value[T](try_get_value: Callable[[], Optional[T]], value_description: str,
                      timeout_millis: int = 5 * 1000) -> T:
    milliseconds_since_epoch = get_epoch_milliseconds()

    expiry_time = milliseconds_since_epoch + timeout_millis

    value: Optional[T] = None

    while value is None and get_epoch_milliseconds() < expiry_time:
        value = try_get_value()

    assert value is not None, f'Timed out waiting for {value_description}'

    return value


def get_epoch_milliseconds() -> int:
    return int(round(time() * 1000))
