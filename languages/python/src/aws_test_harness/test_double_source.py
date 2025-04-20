from logging import Logger
from typing import Dict
from unittest.mock import Mock

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.s3.s3_bucket import S3Bucket


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    __test_double_mocks: Dict[str, Mock] = dict()

    __invocation_handling_task_scheduler: RepeatingTaskScheduler

    def __init__(self, resource_registry: ResourceRegistry, boto_session: Session, logger: Logger,
                 invocation_post_office: InvocationPostOffice,
                 invocation_handling_task_scheduler: RepeatingTaskScheduler):
        self.__logger = logger
        self.__resource_registry = resource_registry
        self.__boto_session = boto_session
        self.__invocation_handling_task_scheduler = invocation_handling_task_scheduler
        self.__invocation_post_office = invocation_post_office

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        bucket_name = self.__get_test_double_physical_id(test_double_name)
        return S3Bucket(bucket_name, self.__boto_session)

    def state_machine(self, test_double_name: str) -> Mock:
        self.__ensure_invocation_handling_scheduled()

        state_machine_arn = self.__resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessStateMachine'
        )
        mock = Mock()
        self.__test_double_mocks[state_machine_arn] = mock
        return mock

    def __get_invocation_result(self, invocation: Invocation):
        # TODO: Handle unknown invocation target
        matching_mock = self.__test_double_mocks[invocation.target]
        # TODO: Pass invocation input to mock
        return matching_mock()

    def __ensure_invocation_handling_scheduled(self):
        if not self.__invocation_handling_task_scheduler.scheduled():
            invocation_handler = InvocationHandler(self.__invocation_post_office, self.__get_invocation_result)
            self.__invocation_handling_task_scheduler.schedule(invocation_handler.handle_pending_invocation)

    def __get_test_double_physical_id(self, test_double_name: str) -> str:
        return self.__resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessS3Bucket'
        )
