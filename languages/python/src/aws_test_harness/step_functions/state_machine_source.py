from logging import Logger

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine import StateMachine


class StateMachineSource:

    def __init__(self, resource_registry: ResourceRegistry, logger: Logger, boto_session: Session):
        self.__boto_session = boto_session
        self.__logger = logger
        self.__resource_registry = resource_registry

    def get(self, cfn_logical_resource_id: str) -> StateMachine:
        state_machine_arn = self.__resource_registry.get_physical_resource_id(cfn_logical_resource_id)
        return StateMachine(state_machine_arn, self.__boto_session, self.__logger)
