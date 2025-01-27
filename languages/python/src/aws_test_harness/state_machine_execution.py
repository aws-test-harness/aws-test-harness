from logging import Logger
from time import sleep

from mypy_boto3_stepfunctions.client import SFNClient
from mypy_boto3_stepfunctions.type_defs import StartExecutionOutputTypeDef

from aws_test_harness.state_machine_execution_result import StateMachineExecutionResult


class StateMachineExecution:
    def __init__(self, step_functions_client: SFNClient, logger: Logger):
        self.__step_functions_client = step_functions_client
        self.__logger = logger

    def wait_for_completion(self, start_execution_result: StartExecutionOutputTypeDef) -> StateMachineExecutionResult:
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
