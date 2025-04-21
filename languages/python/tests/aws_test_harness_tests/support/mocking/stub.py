from typing import Any, Callable
from unittest.mock import Mock


class Stub:
    def __init__(self, mock: Mock):
        self.__mock = mock

    def always_return(self, value: Any) -> None:
        self.__mock.return_value = value

    def invoke(self, function: Callable[..., Any]) -> None:
        self.__mock.side_effect = function

    def respond_with(self, *values: Any) -> None:
        self.__mock.side_effect = values

    def always_raise(self, exception: BaseException) -> None:
        self.__mock.side_effect = exception
