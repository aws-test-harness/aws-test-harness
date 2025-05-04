from typing import Any
from unittest.mock import Mock
# noinspection PyUnresolvedReferences,PyProtectedMember
from unittest.mock import _CallList


class InspectableSpy:
    def __init__(self, mock: Mock):
        self.__mock = mock

    @property
    def called(self) -> bool:
        return self.__mock.called

    @property
    def call_count(self) -> int:
        return self.__mock.call_count

    @property
    def call_args(self) -> Any:
        return self.__mock.call_args

    @property
    def call_args_list(self) -> _CallList:
        return self.__mock.call_args_list

    @property
    def mock_calls(self) -> _CallList:
        return self.__mock.mock_calls
