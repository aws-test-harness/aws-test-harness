from typing import Dict
from unittest.mock import Mock


class TestDoubleBridge:
    __test_double_mocks: Dict[str, Mock] = dict()

    def get_mock_for(self, invocation_target):
        mock = Mock()
        self.__test_double_mocks[invocation_target] = mock
        return mock

    def get_result_for(self, invocation):
        # TODO: Handle unknown invocation target
        matching_mock = self.__test_double_mocks[invocation.target]
        # TODO: Pass invocation input to mock
        return matching_mock()
