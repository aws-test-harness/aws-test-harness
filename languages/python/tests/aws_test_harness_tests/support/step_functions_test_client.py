from typing import Optional, Dict, Any

from boto3 import Session
from mypy_boto3_stepfunctions import SFNClient
from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef

from aws_test_harness_test_support.step_functions_utils import execute_state_machine


class StepFunctionsTestClient:
    def __init__(self, boto_session: Session):
        self.__sfn_client: SFNClient = boto_session.client('stepfunctions')

    def get_latest_execution_arn(self, state_machine_arn: str) -> Optional[str]:
        list_executions_result = self.__sfn_client.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1
        )

        return list_executions_result['executions'][0]['executionArn'] \
            if list_executions_result['executions'] \
            else None

    def get_execution_input_string(self, state_machine_execution_arn: str) -> str:
        describe_execution_result = self.__describe_execution(state_machine_execution_arn)
        return describe_execution_result['input']

    def get_execution_name(self, state_machine_execution_arn: str) -> str:
        describe_execution_result = self.__describe_execution(state_machine_execution_arn)
        return describe_execution_result['name']

    def __describe_execution(self, state_machine_execution_arn: str) -> DescribeExecutionOutputTypeDef:
        return self.__sfn_client.describe_execution(
            executionArn=state_machine_execution_arn
        )

    def execute_state_machine(self, state_machine_arn: str,
                              execution_input: Dict[str, Any]) -> DescribeExecutionOutputTypeDef:
        return execute_state_machine(state_machine_arn, self.__sfn_client, execution_input)
