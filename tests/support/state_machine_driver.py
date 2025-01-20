import json
from logging import Logger
from time import sleep
from typing import Dict
from uuid import uuid4

from boto3 import Session

from support.cloudformation_driver import CloudFormationDriver
from support.state_machine_execution_result import StateMachineExecutionResult


class StateMachineDriver:
    def __init__(self, cloudformation_driver: CloudFormationDriver, boto_session: Session, logger: Logger):
        self.__cloudformation_driver = cloudformation_driver
        self.__logger = logger
        self.__step_functions_client = boto_session.client('stepfunctions')

    def start_execution(self, execution_input: Dict[str, any], state_machine_logic_id: str,
                        cloudformation_stack_name: str):
        state_machine_arn = self.__cloudformation_driver.get_physical_resource_id(
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
