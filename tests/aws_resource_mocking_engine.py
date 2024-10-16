from typing import Callable, Dict
from unittest.mock import Mock, create_autospec

from boto3 import Session

from cloudformation_stack import CloudFormationStack
from lambda_function_event_listener import LambdaFunctionEventListener


class AWSResourceMockingEngine:
    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session: Session):
        self.__cloudformation_stack = cloudformation_stack

        self.__lambda_function_event_listener = LambdaFunctionEventListener(
            boto_session,
            cloudformation_stack.get_physical_resource_id_for(f'TestDoubles::EventsQueue'),
            cloudformation_stack.get_physical_resource_id_for(f'TestDoubles::ResultsQueue')
        )

    def start(self):
        self.__lambda_function_event_listener.start()

    def reset(self):
        self.__lambda_function_event_listener.reset()

    def stop_listening(self):
        self.__lambda_function_event_listener.stop()

    def mock_a_lambda_function(self, logical_resource_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        function_physical_resource_id = self.__cloudformation_stack.get_physical_resource_id_for(
            f'TestDoubles::{logical_resource_id}'
        )

        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_lambda_function: Mock = create_autospec(lambda_handler, name=logical_resource_id)
        mock_lambda_function.side_effect = event_handler

        self.__lambda_function_event_listener.register_function(function_physical_resource_id, mock_lambda_function)

        return mock_lambda_function
