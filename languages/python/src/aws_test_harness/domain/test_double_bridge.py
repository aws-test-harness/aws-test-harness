from typing import Dict, Any
from unittest.mock import Mock

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException


class TestDoubleBridge:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, aws_resource_registry: AwsResourceRegistry):
        self.__aws_resource_registry = aws_resource_registry
        self.__test_double_mocks: Dict[str, Mock] = dict()

    def get_mock_for(self, resource_id: str) -> Mock:
        mock = Mock()
        resource_arn = self.__aws_resource_registry.get_resource_arn(resource_id)
        self.__test_double_mocks[resource_arn] = mock
        return mock

    def get_result_for(self, invocation: Invocation) -> Any:
        matching_mock = self.__test_double_mocks.get(invocation.target)

        if matching_mock is None:
            raise UnknownInvocationTargetException(f'Invocation target "{invocation.target}" has not been mocked')

        return matching_mock(invocation.parameters['input'])

    def reset(self) -> None:
        self.__test_double_mocks = dict()
