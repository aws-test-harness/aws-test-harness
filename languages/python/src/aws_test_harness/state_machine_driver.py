import json
from logging import Logger
from typing import Dict, Any
from uuid import uuid4

from boto3 import Session

from aws_test_harness.cloudformation_resource_registry import CloudFormationResourceRegistry
from aws_test_harness.state_machine_execution import StateMachineExecution
from aws_test_harness.state_machine_execution_result import StateMachineExecutionResult


class StateMachineDriver:
    def __init__(self, cloudformation_resource_registry: CloudFormationResourceRegistry, boto_session: Session,
                 logger: Logger):
        self.__logger = logger
        self.__step_functions_client = boto_session.client('stepfunctions')
        self.__cloudformation_resource_registry = cloudformation_resource_registry

    def start_execution(self, execution_input: Dict[str, Any], state_machine_logic_id: str,
                        cloudformation_stack_name: str):
        state_machine_arn = self.__cloudformation_resource_registry.get_physical_resource_id(
            cloudformation_stack_name,
            state_machine_logic_id)

        self.__logger.info('Starting state machine execution...')
        start_execution_result = self.__step_functions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=f'test-{uuid4()}',
            input=json.dumps(execution_input)
        )

        execution = StateMachineExecution(self.__step_functions_client, self.__logger)

        return execution.wait_for_completion(start_execution_result)
