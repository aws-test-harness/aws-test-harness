from logging import Logger
from typing import Optional

from boto3 import Session

from aws_test_harness.infrastructure.cloudformation_aws_resource_registry import CloudFormationAwsResourceRegistry
from aws_test_harness.infrastructure.boto_aws_resource_factory import BotoAwsResourceFactory
from aws_test_harness.infrastructure.serverless_invocation_post_office import ServerlessInvocationPostOffice
from aws_test_harness.infrastructure.thread_based_repeating_task_scheduler import ThreadBasedRepeatingTaskScheduler
from aws_test_harness.step_functions.state_machine import StateMachine
from aws_test_harness.test_double_source import TestDoubleSource


class TestHarness:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, test_stack_name: str, logger: Logger, aws_profile: Optional[str] = None):
        self.__boto_session = Session(profile_name=aws_profile)
        self.__logger = logger
        self.__aws_resource_registry = CloudFormationAwsResourceRegistry(test_stack_name, self.__boto_session)
        self.__test_double_source = TestDoubleSource(
            self.__aws_resource_registry,
            ServerlessInvocationPostOffice(
                self.__aws_resource_registry.get_resource_arn('AWSTestHarnessTestDoubleInvocationQueue'),
                self.__aws_resource_registry.get_resource_arn('AWSTestHarnessTestDoubleInvocationTable'),
                self.__boto_session,
                logger
            ),
            ThreadBasedRepeatingTaskScheduler(self.__logger),
            BotoAwsResourceFactory(self.__boto_session, self.__aws_resource_registry)
        )

    @property
    def test_doubles(self) -> TestDoubleSource:
        return self.__test_double_source

    def state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        state_machine_arn = self.__aws_resource_registry.get_resource_arn(cfn_logical_resource_id)
        return StateMachine(state_machine_arn, self.__boto_session, self.__logger)

    def tear_down(self) -> None:
        self.__test_double_source.reset()
