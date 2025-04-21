from typing import TypeVar, Callable, cast, Any
from unittest.mock import create_autospec

from aws_test_harness_tests.support.mocking.inspectable_spy import InspectableSpy
from aws_test_harness_tests.support.mocking.stub import Stub
from aws_test_harness_tests.support.mocking.verifiable_spy import VerifiableSpy

T = TypeVar("T")


# Have to use Callable[[], T] instead of Type[T] so T can be abstract
# See https://github.com/python/mypy/issues/4717#issuecomment-2453711357
def mock_class[T](cls: Callable[[], T]) -> T:
    return cast(T, create_autospec(spec=cls, instance=True))


def inspect(mock: Any):
    return InspectableSpy(mock)


def verify(mock: Any) -> VerifiableSpy:
    return VerifiableSpy(mock)


def when_calling(mock: Any) -> Stub:
    return Stub(mock)
