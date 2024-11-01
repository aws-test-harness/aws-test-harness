from typing import Callable, Dict
from unittest.mock import Mock, create_autospec
from uuid import uuid4

from boto3 import Session

from .aws_test_double_driver import AWSTestDoubleDriver
from .lambda_function_event_listener import LambdaFunctionEventListener


class AWSResourceMockingEngine:
    __mocking_session_id: str = None
    __lambda_function_event_listener: LambdaFunctionEventListener = None

    def __init__(self, test_double_driver: AWSTestDoubleDriver, boto_session: Session):
        self.__mock_event_handlers: Dict[str, Mock] = {}
        self.__test_double_driver = test_double_driver
        self.__boto_session = boto_session

    def reset(self):
        if self.__lambda_function_event_listener:
            self.__lambda_function_event_listener.stop()

        self.__set_mocking_session_id()

        self.__lambda_function_event_listener = LambdaFunctionEventListener(self.__test_double_driver,
                                                                            self.__boto_session,
                                                                            lambda: self.__mocking_session_id)

        self.__lambda_function_event_listener.start()

    def mock_a_lambda_function(self, function_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_event_handler: Mock = create_autospec(lambda_handler, name=function_id)
        mock_event_handler.side_effect = event_handler

        self.__lambda_function_event_listener.register_event_handler(
            self.__test_double_driver.get_lambda_function_name(function_id),
            mock_event_handler
        )

        self.__mock_event_handlers[function_id] = mock_event_handler

        return mock_event_handler

    def __set_mocking_session_id(self) -> str:
        self.__mocking_session_id = str(uuid4())
        self.__test_double_driver.test_context_bucket.put_object('test-id', self.__mocking_session_id)
        return self.__mocking_session_id

    def get_mock_lambda_function(self, logical_resource_id: str) -> Mock:
        return self.__mock_event_handlers[logical_resource_id]
