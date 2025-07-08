from typing import Callable, Dict
from unittest.mock import Mock, create_autospec
from uuid import uuid4

from boto3 import Session

from .aws_test_double_driver import AWSTestDoubleDriver
from .message_listener import MessageListener


class AWSResourceMockingEngine:
    __mocking_session_id: str = None
    __message_listener: MessageListener = None

    def __init__(self, test_double_driver: AWSTestDoubleDriver, boto_session: Session):
        self.__mock_event_handlers: Dict[str, Mock] = {}
        self.__test_double_driver = test_double_driver
        self.__boto_session = boto_session

    def reset(self):
        if self.__message_listener:
            self.__message_listener.stop()

        self.__set_mocking_session_id()

        self.__message_listener = MessageListener(self.__test_double_driver, self.__boto_session,
                                                  lambda: self.__mocking_session_id)

        self.__message_listener.start()

    def mock_a_lambda_function(self, function_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_event_handler: Mock = create_autospec(lambda_handler, name=function_id)
        mock_event_handler.side_effect = event_handler

        self.__message_listener.register_lambda_function_event_handler(
            self.__test_double_driver.get_lambda_function_name(function_id),
            mock_event_handler
        )

        mock_id = self.__get_lambda_function_mock_id(function_id)
        self.__mock_event_handlers[mock_id] = mock_event_handler

        return mock_event_handler

    def mock_a_state_machine(self, state_machine_id,
                             handle_execution_input: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        def execution_input_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock: Mock = create_autospec(execution_input_handler, name=state_machine_id)
        mock.side_effect = handle_execution_input

        self.__message_listener.register_state_machine_execution_input_handler(
            self.__test_double_driver.get_state_machine_name(state_machine_id),
            mock
        )

        mock_id = self.__get_state_machine_mock_id(state_machine_id)
        self.__mock_event_handlers[mock_id] = mock

        return mock

    def mock_an_ecs_task(self, task_family: str,
                         task_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        def ecs_task_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock: Mock = create_autospec(ecs_task_handler, name=task_family)
        mock.side_effect = task_handler

        self.__message_listener.register_ecs_task_handler(task_family, mock)

        mock_id = self.__get_ecs_task_mock_id(task_family)
        self.__mock_event_handlers[mock_id] = mock

        return mock

    def __set_mocking_session_id(self) -> str:
        self.__mocking_session_id = str(uuid4())
        self.__test_double_driver.test_context_bucket.put_object('test-id', self.__mocking_session_id)
        return self.__mocking_session_id

    def get_mock_lambda_function(self, function_id: str) -> Mock:
        mock_id = self.__get_lambda_function_mock_id(function_id)
        return self.__mock_event_handlers[mock_id]

    def get_mock_state_machine(self, state_machine_id: str) -> Mock:
        mock_id = self.__get_state_machine_mock_id(state_machine_id)
        return self.__mock_event_handlers[mock_id]

    def get_mock_ecs_task(self, task_family: str) -> Mock:
        mock_id = self.__get_ecs_task_mock_id(task_family)
        return self.__mock_event_handlers[mock_id]

    @staticmethod
    def __get_lambda_function_mock_id(state_machine_id: str) -> str:
        return f'LambdaFunction::{state_machine_id}'

    @staticmethod
    def __get_state_machine_mock_id(state_machine_id: str) -> str:
        return f'StateMachine::{state_machine_id}'

    @staticmethod
    def __get_ecs_task_mock_id(task_family: str) -> str:
        return f'ECSTask::{task_family}'
