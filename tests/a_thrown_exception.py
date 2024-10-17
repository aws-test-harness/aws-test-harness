from dataclasses import dataclass


@dataclass
class AThrownException:
    message: str


def an_exception_thrown_with_message(exception_message) -> AThrownException:
    return AThrownException(exception_message)
