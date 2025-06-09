from typing import Optional

from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.invocation_target_twin_service import InvocationTargetTwinService
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.state_machine_twin import StateMachineTwin, StateMachineExecutionHandler


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, aws_resource_registry: AwsResourceRegistry, invocation_post_office: InvocationPostOffice,
                 invocation_handling_scheduler: RepeatingTaskScheduler,
                 aws_resource_factory: AwsResourceFactory):
        self.__aws_resource_factory = aws_resource_factory
        self.__invocation_handling_scheduler: RepeatingTaskScheduler = invocation_handling_scheduler
        self.__invocation_target_twin_service = InvocationTargetTwinService(aws_resource_registry)
        self.__invocation_handler = InvocationHandler(
            invocation_post_office,
            self.__invocation_target_twin_service.generate_result_for_invocation
        )

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        return self.__aws_resource_factory.get_s3_bucket(f'{test_double_name}AWSTestHarnessS3Bucket')

    def state_machine(self, state_machine_name: str,
                      execution_handler: Optional[StateMachineExecutionHandler] = None) -> StateMachineTwin:
        if not self.__invocation_handling_scheduler.scheduled():
            self.__invocation_handling_scheduler.schedule(self.__invocation_handler.handle_pending_invocation)

        return self.__invocation_target_twin_service.create_twin_for_state_machine(state_machine_name,
                                                                                   execution_handler)

    def reset(self) -> None:
        self.__invocation_handling_scheduler.reset_schedule()
        self.__invocation_target_twin_service.reset()
