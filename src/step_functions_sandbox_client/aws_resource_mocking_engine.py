from typing import Callable, Dict
from unittest.mock import Mock, create_autospec
from uuid import uuid4

from boto3 import Session
from mypy_boto3_s3 import S3Client

from .cloudformation_stack import CloudFormationStack
from .lambda_function_event_listener import LambdaFunctionEventListener


class AWSResourceMockingEngine:
    __mocking_session_id: str = None
    __lambda_function_event_listener: LambdaFunctionEventListener = None

    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session: Session):
        self.__cloudformation_stack = cloudformation_stack
        self.__boto_session = boto_session

        self.__s3_client: S3Client = self.__boto_session.client('s3')

        self.__test_context_s3_bucket_name = self.__cloudformation_stack.get_physical_resource_id_for(
            'TestDoubles::TestContextBucket'
        )

        self.__events_queue_url = cloudformation_stack.get_physical_resource_id_for(f'TestDoubles::EventsQueue')
        self.__results_queue_url = cloudformation_stack.get_physical_resource_id_for(f'TestDoubles::ResultsQueue')

    def reset(self):
        if self.__lambda_function_event_listener:
            self.__lambda_function_event_listener.stop()

        self.__generate_new_mocking_session_id()

        self.__lambda_function_event_listener = LambdaFunctionEventListener(
            self.__boto_session,
            self.__events_queue_url,
            self.__results_queue_url,
            lambda: self.__mocking_session_id
        )

        self.__lambda_function_event_listener.start()

    def mock_a_lambda_function(self, logical_resource_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        function_physical_resource_id = self.__cloudformation_stack.get_physical_resource_id_for(
            f'TestDoubles::{logical_resource_id}'
        )

        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_lambda_function: Mock = create_autospec(lambda_handler, name=logical_resource_id)
        mock_lambda_function.side_effect = event_handler

        self.__lambda_function_event_listener.register_function(function_physical_resource_id, logical_resource_id,
                                                                mock_lambda_function)

        return mock_lambda_function

    def __generate_new_mocking_session_id(self) -> str:
        self.__mocking_session_id = str(uuid4())

        self.__s3_client.put_object(
            Bucket=self.__test_context_s3_bucket_name,
            Key='test-id',
            Body=self.__mocking_session_id
        )

        return self.__mocking_session_id

    def get_mock_lambda_function(self, logical_resource_id: str) -> Mock:
        return self.__lambda_function_event_listener.get_mock_lambda_function(logical_resource_id)
