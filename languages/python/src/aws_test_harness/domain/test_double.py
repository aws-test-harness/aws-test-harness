from abc import ABCMeta, abstractmethod
from typing import Any
from unittest.mock import Mock

from aws_test_harness.domain.invocation import Invocation


class TestDouble(metaclass=ABCMeta):
    def __init__(self) -> None:
        self._mock = Mock()

    @abstractmethod
    def get_result_for(self, invocation: Invocation) -> Any:
        pass

    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
        self._mock.assert_called_once_with(*args, **kwargs)

    @property
    def call_count(self) -> int:
        return self._mock.call_count
