from unittest.mock import Mock

from boto3 import Session

from aws_test_harness.cloudformation.cloudformation_resource_registry import CloudFormationResourceRegistry
from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.domain.test_double_bridge import TestDoubleBridge
from aws_test_harness.infrastructure.boto_s3_bucket import BotoS3Bucket


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    __invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler

    def __init__(self, resource_registry: CloudFormationResourceRegistry, invocation_post_office: InvocationPostOffice,
                 invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
                 aws_resource_factory: AwsResourceFactory):
        self.__aws_resource_factory = aws_resource_factory
        self.__resource_registry = resource_registry
        self.__test_double_bridge = TestDoubleBridge()
        self.__invocation_handler = InvocationHandler(invocation_post_office, self.__test_double_bridge.get_result_for)
        self.__invocation_handler_repeating_task_scheduler = invocation_handler_repeating_task_scheduler

    def s3_bucket(self, test_double_name: str) -> BotoS3Bucket:
        return self.__aws_resource_factory.get_s3_bucket(f'{test_double_name}AWSTestHarnessS3Bucket')

    def state_machine(self, test_double_name: str) -> Mock:
        if not self.__invocation_handler_repeating_task_scheduler.scheduled():
            self.__invocation_handler_repeating_task_scheduler.schedule(
                self.__invocation_handler.handle_pending_invocation)

        state_machine_arn = self.__resource_registry.get_physical_resource_id(
            f'{test_double_name}AWSTestHarnessStateMachine'
        )

        return self.__test_double_bridge.get_mock_for(state_machine_arn)
