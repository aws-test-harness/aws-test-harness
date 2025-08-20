from typing import Callable, Dict, List
from unittest.mock import Mock, create_autospec
from uuid import uuid4

from boto3 import Session

from .a_state_machine_execution_failure import AStateMachineExecutionFailure
from .a_thrown_exception import AThrownException
from .exit_code import ExitCode
from .aws_test_double_driver import AWSTestDoubleDriver
from .message_listener import MessageListener
from .task_context import TaskContext


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
                               event_handler: Callable[[Dict[str, any]], Dict[str, any] | AThrownException]) -> Mock:
        def lambda_handler(_: Dict[str, any]) -> Dict[str, any] | AThrownException:
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
                             handle_execution_input: Callable[
                                 [Dict[str, any]], Dict[str, any] | AStateMachineExecutionFailure]) -> Mock:
        def execution_input_handler(_: Dict[str, any]) -> Dict[str, any] | AStateMachineExecutionFailure:
            pass

        mock: Mock = create_autospec(execution_input_handler, name=state_machine_id)
        mock.side_effect = handle_execution_input

        self.__message_listener.register_state_machine_execution_input_handler(
            self.__test_double_driver.get_state_machine_arn(state_machine_id),
            mock
        )

        mock_id = self.__get_state_machine_mock_id(state_machine_id)
        self.__mock_event_handlers[mock_id] = mock

        return mock

    def mock_an_ecs_task_container(self, task: str, container: str,
                                   handler: Callable[[TaskContext], ExitCode]) -> Mock:
        def ecs_task_handler(_: List[str]) -> ExitCode:
            pass

        mock: Mock = create_autospec(ecs_task_handler, name=task)
        mock.side_effect = handler

        task_definition_arn = self.__test_double_driver.get_task_definition_arn(task)
        self.__message_listener.register_ecs_task_container_handler(task_definition_arn, container, mock)

        mock_id = self.__get_ecs_task_container_mock_id(task, container)
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

    def get_mock_ecs_task_container(self, task: str, container: str) -> Mock:
        mock_id = self.__get_ecs_task_container_mock_id(task, container)
        return self.__mock_event_handlers[mock_id]

    @staticmethod
    def __get_lambda_function_mock_id(state_machine_id: str) -> str:
        return f'LambdaFunction::{state_machine_id}'

    @staticmethod
    def __get_state_machine_mock_id(state_machine_id: str) -> str:
        return f'StateMachine::{state_machine_id}'

    @staticmethod
    def __get_ecs_task_container_mock_id(task_family: str, container: str) -> str:
        return f'ECSTask::{task_family}#{container}'
