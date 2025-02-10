from logging import Logger
from typing import Optional

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine import StateMachine
from aws_test_harness.test_double_source import TestDoubleSource


class TestHarness:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, test_stack_name: str, logger: Logger, aws_profile: Optional[str] = None):
        self.__boto_session = Session(profile_name=aws_profile)
        self.__logger = logger
        self.__test_resource_registry = ResourceRegistry(test_stack_name, self.__boto_session)
        self.__test_double_source = TestDoubleSource(self.__test_resource_registry, self.__boto_session)

    @property
    def test_doubles(self) -> TestDoubleSource:
        return self.__test_double_source

    def state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        state_machine_arn = self.__test_resource_registry.get_physical_resource_id(cfn_logical_resource_id)
        return StateMachine(state_machine_arn, self.__boto_session, self.__logger)
