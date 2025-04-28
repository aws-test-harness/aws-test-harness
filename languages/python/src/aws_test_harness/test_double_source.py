from unittest.mock import Mock

from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.test_double_bridge import TestDoubleBridge


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    __invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler

    def __init__(self, aws_resource_registry: AwsResourceRegistry, invocation_post_office: InvocationPostOffice,
                 invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
                 aws_resource_factory: AwsResourceFactory):
        self.__aws_resource_factory = aws_resource_factory
        self.__invocation_handler_repeating_task_scheduler = invocation_handler_repeating_task_scheduler
        self.__test_double_bridge = TestDoubleBridge(aws_resource_registry)
        self.__invocation_handler = InvocationHandler(invocation_post_office, self.__test_double_bridge.get_result_for)

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        return self.__aws_resource_factory.get_s3_bucket(f'{test_double_name}AWSTestHarnessS3Bucket')

    def state_machine(self, test_double_name: str) -> Mock:
        if not self.__invocation_handler_repeating_task_scheduler.scheduled():
            self.__invocation_handler_repeating_task_scheduler.schedule(
                self.__invocation_handler.handle_pending_invocation
            )

        return self.__test_double_bridge.get_mock_for(f'{test_double_name}AWSTestHarnessStateMachine')

    def reset(self) -> None:
        self.__invocation_handler_repeating_task_scheduler.reset_schedule()
