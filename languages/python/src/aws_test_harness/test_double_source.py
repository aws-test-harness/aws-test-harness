from typing import Optional, Dict, Any

from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.test_double_state_machine import TestDoubleStateMachine, StateMachineExecutionHandler
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, aws_resource_registry: AwsResourceRegistry, invocation_post_office: InvocationPostOffice,
                 invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
                 aws_resource_factory: AwsResourceFactory):
        self.__aws_resource_factory = aws_resource_factory
        self.__invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler = invocation_handler_repeating_task_scheduler
        self.__test_doubles: Dict[str, TestDoubleStateMachine] = dict()
        self.__aws_resource_registry = aws_resource_registry

        def get_result_for(invocation: Invocation) -> Any:
            test_double = self.__test_doubles.get(invocation.target)

            if test_double is None:
                raise UnknownInvocationTargetException(
                    f'No test double has been configured for invocation target "{invocation.target}"'
                )

            return test_double.get_result_for(invocation)

        self.__invocation_handler = InvocationHandler(invocation_post_office, get_result_for)

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        return self.__aws_resource_factory.get_s3_bucket(f'{test_double_name}AWSTestHarnessS3Bucket')

    def state_machine(self, test_double_name: str,
                      execution_handler: Optional[StateMachineExecutionHandler] = None) -> TestDoubleStateMachine:
        if not self.__invocation_handler_repeating_task_scheduler.scheduled():
            self.__invocation_handler_repeating_task_scheduler.schedule(
                self.__invocation_handler.handle_pending_invocation
            )

        resource_arn = self.__aws_resource_registry.get_resource_arn(f'{test_double_name}AWSTestHarnessStateMachine')
        test_double = TestDoubleStateMachine(execution_handler)
        self.__test_doubles[resource_arn] = test_double
        return test_double

    def reset(self) -> None:
        self.__invocation_handler_repeating_task_scheduler.reset_schedule()
        self.__test_doubles = dict()
