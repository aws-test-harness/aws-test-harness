import json
from logging import Logger
from time import sleep
from typing import Dict, Any
from uuid import uuid4

from boto3 import Session

from aws_test_harness.cloudformation_resource_registry import CloudFormationResourceRegistry
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

        while True:
            describe_execution_result = self.__step_functions_client.describe_execution(
                executionArn=start_execution_result['executionArn']
            )

            status = describe_execution_result['status']

            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                self.__logger.info('State machine execution completed.')
                return StateMachineExecutionResult(
                    status=status,
                    output=describe_execution_result.get('output'),
                    error=describe_execution_result.get('error'),
                    cause=describe_execution_result.get('cause')
                )

            sleep(0.1)
