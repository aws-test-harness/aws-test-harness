from typing import Any, Sequence
from unittest.mock import Mock
# noinspection PyUnresolvedReferences,PyProtectedMember
from unittest.mock import _Call


class VerifiableSpy:
    def __init__(self, mock: Mock):
        self.__mock = mock

    def was_not_called(self) -> None:
        self.__mock.assert_not_called()

    def was_called(self) -> None:
        self.__mock.assert_called()

    def was_called_once(self) -> None:
        self.__mock.assert_called_once()

    def was_called_with(self, /, *args: Any, **kwargs: Any) -> None:
        self.__mock.assert_called_with(*args, **kwargs)

    def was_called_once_with(self, /, *args: Any, **kwargs: Any) -> None:
        self.__mock.assert_called_once_with(*args, **kwargs)

    def had_calls(self, calls: Sequence[_Call], any_order: bool = False) -> None:
        self.__mock.assert_has_calls(calls, any_order)

    def had_call(self, /, *args: Any, **kwargs: Any) -> None:
        return self.__mock.assert_any_call(*args, **kwargs)
