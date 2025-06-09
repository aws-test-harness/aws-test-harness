from logging import Logger
from time import sleep
from typing import Optional

from mypy_boto3_stepfunctions import SFNClient
from mypy_boto3_stepfunctions.literals import ExecutionStatusType
from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef

from aws_test_harness.domain.state_machine_execution import StateMachineExecution


class BotoStateMachineExecution(StateMachineExecution):
    def __init__(self, execution_arn: str, step_functions_client: SFNClient, logger: Logger):
        self.__step_functions_client = step_functions_client
        self.__execution_arn = execution_arn
        self.__logger = logger

    @property
    def status(self) -> Optional[str]:
        describe_execution_result = self.__describe_execution()
        return self.__get_status(describe_execution_result)

    @property
    def output(self) -> Optional[str]:
        describe_execution_result = self.__describe_execution()
        return describe_execution_result.get('output')

    @property
    def error(self) -> Optional[str]:
        describe_execution_result = self.__describe_execution()
        return describe_execution_result.get('error')

    @property
    def cause(self) -> Optional[str]:
        describe_execution_result = self.__describe_execution()
        return describe_execution_result.get('cause')

    def wait_for_completion(self) -> None:
        while True:
            describe_execution_result = self.__describe_execution()
            status = self.__get_status(describe_execution_result)

            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                self.__logger.info('State machine execution completed.')
                return

            sleep(0.1)

    def __describe_execution(self) -> DescribeExecutionOutputTypeDef:
        return self.__step_functions_client.describe_execution(
            executionArn=self.__execution_arn
        )

    @staticmethod
    def __get_status(describe_execution_result: DescribeExecutionOutputTypeDef) -> ExecutionStatusType:
        return describe_execution_result['status']
