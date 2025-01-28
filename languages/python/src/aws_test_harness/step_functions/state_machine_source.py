from logging import Logger
from typing import Optional

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine import StateMachine


class StateMachineSource:

    def __init__(self, stack_name: str, logger: Logger, aws_profile: Optional[str] = None):
        self.__stack_name = stack_name
        self.__boto_session = Session(profile_name=aws_profile)
        self.__resource_registry = ResourceRegistry(stack_name, self.__boto_session)
        self.__logger = logger

    def get_state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        state_machine_arn = self.__resource_registry.get_physical_resource_id(cfn_logical_resource_id)
        return StateMachine(state_machine_arn, self.__boto_session, self.__logger)
