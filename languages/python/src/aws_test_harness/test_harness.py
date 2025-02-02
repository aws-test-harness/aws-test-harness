from logging import Logger
from typing import Optional

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine import StateMachine
from aws_test_harness.step_functions.state_machine_source import StateMachineSource
from aws_test_harness.test_double_source import TestDoubleSource


# TODO: Retrofit test coverage
class TestHarness:
    def __init__(self, test_stack_name: str, logger: Logger, aws_profile: Optional[str] = None):
        boto_session = Session(profile_name=aws_profile)
        test_resource_registry = ResourceRegistry(test_stack_name, boto_session)

        self.__state_machine_source = StateMachineSource(test_resource_registry, logger, boto_session)

        def create_test_double_resource_registry() -> ResourceRegistry:
            test_double_stack_name = test_resource_registry.get_physical_resource_id('TestDoubles')
            return ResourceRegistry(test_double_stack_name, boto_session)

        self.__test_double_source = TestDoubleSource(create_test_double_resource_registry, boto_session)

    @property
    def test_doubles(self) -> TestDoubleSource:
        return self.__test_double_source

    def state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        return self.__state_machine_source.get(cfn_logical_resource_id)
