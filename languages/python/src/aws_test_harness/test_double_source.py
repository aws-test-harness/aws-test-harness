import threading
from datetime import datetime, timedelta
from logging import getLogger
from threading import Thread
from unittest.mock import Mock

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_sqs.service_resource import SQSServiceResource

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.s3.s3_bucket import S3Bucket
from conftest import boto_session


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, test_double_resource_registry: ResourceRegistry, boto_session: Session, logger):
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

        def handle_invocation():
            try:
                messages = invocation_queue.receive_messages(
                    #TODO: Shorten wait time
                    MessageAttributeNames=['All'], MaxNumberOfMessages=1, WaitTimeSeconds=10
                )
                messages[0].delete()
                #TODO: Filter for invocation target
                #TODO: Pass invocation input to mock
                result = mock()
                invocation_table.put_item(Item=dict(
                    id=messages[0].message_attributes['InvocationId']['StringValue'],
                    result=dict(value=result),
                    ttl=int((datetime.now() + timedelta(days=1)).timestamp())
                ))
            except BaseException as e:
                self.__logger.exception('Uncaught exception in invocation-handling thread', exc_info=e)

        thread = Thread(target=handle_invocation, daemon=True)
        thread.start()

        return mock

    def __get_test_double_physical_id(self, test_double_name: str) -> str:
        return self.__test_double_resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessS3Bucket'
        )
