from typing import Callable, Dict
from unittest.mock import Mock, create_autospec
from uuid import uuid4

from boto3 import Session

from .aws_test_double_driver import AWSTestDoubleDriver
from .cloudformation_stack import CloudFormationStack
from .lambda_function_event_listener import LambdaFunctionEventListener


class AWSResourceMockingEngine:
    __mocking_session_id: str = None
    __lambda_function_event_listener: LambdaFunctionEventListener = None

    def __init__(self, cloudformation_stack: CloudFormationStack, test_double_driver: AWSTestDoubleDriver,
                 boto_session: Session):
        self.__mock_lambda_functions_by_logical_id: Dict[str, Mock] = {}
        self.__cloudformation_stack = cloudformation_stack
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

    def mock_a_lambda_function(self, logical_resource_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        function_physical_resource_id = self.__cloudformation_stack.get_physical_resource_id_for(
            logical_resource_id
        )

        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_lambda_function: Mock = create_autospec(lambda_handler, name=logical_resource_id)
        mock_lambda_function.side_effect = event_handler

        self.__lambda_function_event_listener.register_event_handler(function_physical_resource_id,
                                                                     lambda event: mock_lambda_function(event))
        self.__mock_lambda_functions_by_logical_id[logical_resource_id] = mock_lambda_function

        return mock_lambda_function

    def __set_mocking_session_id(self) -> str:
        self.__mocking_session_id = str(uuid4())
        self.__test_double_driver.test_context_bucket.put_object('test-id', self.__mocking_session_id)
        return self.__mocking_session_id

    def get_mock_lambda_function(self, logical_resource_id: str) -> Mock:
        return self.__mock_lambda_functions_by_logical_id[logical_resource_id]
