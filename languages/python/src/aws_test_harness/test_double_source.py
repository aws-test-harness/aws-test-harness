from datetime import datetime, timedelta
from logging import Logger
from threading import Thread
from typing import Dict
from unittest.mock import Mock

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_sqs.service_resource import SQSServiceResource

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.s3.s3_bucket import S3Bucket


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    __test_double_mocks: Dict[str, Mock] = dict()

    __listening_for_invocations: bool = False

    def __init__(self, test_double_resource_registry: ResourceRegistry, boto_session: Session, logger: Logger):
        self.__logger = logger
        self.__test_double_resource_registry = test_double_resource_registry
        self.__boto_session = boto_session

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        bucket_name = self.__get_test_double_physical_id(test_double_name)
        return S3Bucket(bucket_name, self.__boto_session)

    def state_machine(self, test_double_name: str) -> Mock:
        sqs_resource: SQSServiceResource = self.__boto_session.resource('sqs')
        invocation_queue_url = self.__test_double_resource_registry.get_physical_resource_id(
            'AWSTestHarnessTestDoubleInvocationQueue'
        )
        invocation_queue = sqs_resource.Queue(invocation_queue_url)
        dynamodb_resource: DynamoDBServiceResource = self.__boto_session.resource('dynamodb')
        invocation_table_name = self.__test_double_resource_registry.get_physical_resource_id(
            'AWSTestHarnessTestDoubleInvocationTable'
        )
        invocation_table = dynamodb_resource.Table(invocation_table_name)

        mock = Mock()
        state_machine_arn = self.__test_double_resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessStateMachine'
        )

        self.__test_double_mocks[state_machine_arn] = mock

        if not self.__listening_for_invocations:
            def handle_invocation() -> None:
                while True:
                    try:
                        messages = invocation_queue.receive_messages(
                            MessageAttributeNames=['All'],
                            MaxNumberOfMessages=1,
                            WaitTimeSeconds=1
                        )

                        if messages:
                            message = messages[0]
                            message.delete()

                            invocation_target = message.message_attributes['InvocationTarget']['StringValue']

                            # TODO: Handle unknown invocation target
                            matching_mock = self.__test_double_mocks[invocation_target]

                            # TODO: Pass invocation input to mock
                            result = matching_mock()
                            invocation_table.put_item(Item=dict(
                                id=message.message_attributes['InvocationId']['StringValue'],
                                result=dict(value=result),
                                ttl=int((datetime.now() + timedelta(days=1)).timestamp())
                            ))
                    except BaseException as e:
                        self.__logger.exception('Uncaught exception in invocation-handling thread', exc_info=e)

            thread = Thread(target=handle_invocation, daemon=True)
            thread.start()
            self.__listening_for_invocations = True

        return mock

    def __get_test_double_physical_id(self, test_double_name: str) -> str:
        return self.__test_double_resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessS3Bucket'
        )
