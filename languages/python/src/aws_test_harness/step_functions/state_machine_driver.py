import json
from logging import Logger
from typing import Dict, Any
from uuid import uuid4

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine_execution import StateMachineExecution


class StateMachineDriver:
    def __init__(self, resource_registry: ResourceRegistry, boto_session: Session,
                 logger: Logger):
        self.__logger = logger
        self.__step_functions_client = boto_session.client('stepfunctions')
        self.__resource_registry = resource_registry

    def execute(self, execution_input: Dict[str, Any], state_machine_logic_id: str,
                cloudformation_stack_name: str) -> StateMachineExecution:
        execution = self.__start_execution(execution_input, state_machine_logic_id, cloudformation_stack_name)
        execution.wait_for_completion()

        return execution

    def __start_execution(self, execution_input: Dict[str, Any], state_machine_logic_id: str,
                          cloudformation_stack_name: str) -> StateMachineExecution:
        state_machine_arn = self.__resource_registry.get_physical_resource_id(state_machine_logic_id,
                                                                              cloudformation_stack_name)

        self.__logger.info('Starting state machine execution...')
        start_execution_result = self.__step_functions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=f'test-{uuid4()}',
            input=json.dumps(execution_input)
        )

        return StateMachineExecution(start_execution_result['executionArn'], self.__step_functions_client,
                                     self.__logger)
