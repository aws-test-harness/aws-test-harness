from typing import Callable, Dict
from unittest.mock import Mock, create_autospec

from boto3 import Session
from mypy_boto3_sqs import SQSClient

from cloudformation_stack import CloudFormationStack
from lambda_function_listener import LambdaFunctionListener


class AWSResourceMockingEngine:
    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session: Session):
        self.__cloudformation_stack = cloudformation_stack
        self.__mock_lambda_functions: Dict[str, Mock] = {}
        self.__lambda_function_listeners = []
        self.__sqs_client: SQSClient = boto_session.client('sqs')

    def reset(self):
        self.stop_listening()
        self.__mock_lambda_functions = {}
        self.__lambda_function_listeners = []

    def stop_listening(self):
        for listener in self.__lambda_function_listeners:
            listener.stop()

    def mock_a_lambda_function(self, logical_resource_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        function_physical_resource_id = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{logical_resource_id}.Function'
        )

        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_lambda_function: Mock = create_autospec(lambda_handler, name=logical_resource_id)
        self.__mock_lambda_functions[function_physical_resource_id] = mock_lambda_function
        mock_lambda_function.side_effect = event_handler

        events_queue_url = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{logical_resource_id}.EventsQueue'
        )
        results_queue_url = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{logical_resource_id}.ResultsQueue'
        )

        listener = LambdaFunctionListener(events_queue_url, mock_lambda_function, results_queue_url, self.__sqs_client)
        listener.start()

        self.__lambda_function_listeners.append(listener)

        return mock_lambda_function
