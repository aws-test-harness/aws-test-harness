from typing import Dict, Any
from unittest.mock import Mock

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation


class TestDoubleBridge:
    __test_double_mocks: Dict[str, Mock] = dict()

    def __init__(self, aws_resource_registry: AwsResourceRegistry):
        self.__aws_resource_registry = aws_resource_registry

    def get_mock_for(self, resource_id: str) -> Mock:
        mock = Mock()
        resource_arn = self.__aws_resource_registry.get_resource_arn(resource_id)
        self.__test_double_mocks[resource_arn] = mock
        return mock

    def get_result_for(self, invocation: Invocation) -> Any:
        # TODO: Handle unknown invocation target
        matching_mock = self.__test_double_mocks[invocation.target]
        # TODO: Pass invocation input to mock
        return matching_mock()
