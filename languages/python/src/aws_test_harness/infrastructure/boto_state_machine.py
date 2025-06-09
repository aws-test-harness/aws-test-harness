import json
from logging import Logger
from typing import Dict, Any
from uuid import uuid4

from boto3 import Session
from mypy_boto3_stepfunctions import SFNClient

from aws_test_harness.domain.state_machine import StateMachine
from aws_test_harness.domain.state_machine_execution import StateMachineExecution
from aws_test_harness.infrastructure.boto_state_machine_execution import BotoStateMachineExecution


class BotoStateMachine(StateMachine):
    def __init__(self, state_machine_arn: str, boto_session: Session, logger: Logger):
        self.__state_machine_arn = state_machine_arn
        self.__logger = logger
        self.__step_functions_client: SFNClient = boto_session.client('stepfunctions')

    def execute(self, execution_input: Dict[str, Any]) -> StateMachineExecution:
        execution = self.__start_execution(execution_input)
        execution.wait_for_completion()

        return execution

    def __start_execution(self, execution_input: Dict[str, Any]) -> StateMachineExecution:
        self.__logger.info('Starting state machine execution...')
        start_execution_result = self.__step_functions_client.start_execution(
            stateMachineArn=self.__state_machine_arn,
            name=f'test-{uuid4()}',
            input=json.dumps(execution_input)
        )

        return BotoStateMachineExecution(start_execution_result['executionArn'], self.__step_functions_client,
                                         self.__logger)
