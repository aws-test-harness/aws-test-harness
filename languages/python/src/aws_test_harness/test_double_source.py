from datetime import datetime, timedelta
from logging import Logger
from typing import Dict, Callable
from unittest.mock import Mock

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.domain.invocation_listener import InvocationListener
from aws_test_harness.s3.s3_bucket import S3Bucket


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    __test_double_mocks: Dict[str, Mock] = dict()

    __listening_for_invocations = False

    def __init__(self, test_double_resource_registry: ResourceRegistry, boto_session: Session, logger: Logger,
                 create_invocation_listener: Callable[[], InvocationListener]):
        self.__logger = logger
        self.__test_double_resource_registry = test_double_resource_registry
        self.__boto_session = boto_session
        self.__create_invocation_listener = create_invocation_listener

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        bucket_name = self.__get_test_double_physical_id(test_double_name)
        return S3Bucket(bucket_name, self.__boto_session)

    def state_machine(self, test_double_name: str) -> Mock:
        state_machine_arn = self.__test_double_resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessStateMachine'
        )
        mock = Mock()
        self.__test_double_mocks[state_machine_arn] = mock

        if not self.__listening_for_invocations:
            invocation_listener = self.__create_invocation_listener()

            dynamodb_resource: DynamoDBServiceResource = self.__boto_session.resource('dynamodb')
            invocation_table_name = self.__test_double_resource_registry.get_physical_resource_id(
                'AWSTestHarnessTestDoubleInvocationTable'
            )
            invocation_table = dynamodb_resource.Table(invocation_table_name)

            def handle_invocation(invocation_target: str, invocation_id: str) -> None:
                # TODO: Handle unknown invocation target
                matching_mock = self.__test_double_mocks[invocation_target]

                # TODO: Pass invocation input to mock
                result = matching_mock()
                invocation_table.put_item(Item=dict(
                    id=invocation_id,
                    result=dict(value=result),
                    ttl=int((datetime.now() + timedelta(days=1)).timestamp())
                ))

            invocation_listener.listen(handle_invocation)
            __listening_for_invocations = True

        return mock

    def __get_test_double_physical_id(self, test_double_name: str) -> str:
        return self.__test_double_resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessS3Bucket'
        )
