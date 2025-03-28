import json
from typing import Dict, Any

from mypy_boto3_stepfunctions.client import SFNClient
from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef

from infrastructure_test_support.eventual_consistency_utils import wait_for_value_matching


def start_state_machine_execution(example_state_machine_arn: str, step_functions_client: SFNClient,
                                  execution_input: Dict[str, Any]) -> str:
    start_execution_result = step_functions_client.start_execution(
        stateMachineArn=example_state_machine_arn,
        input=json.dumps(execution_input)
    )

    return start_execution_result['executionArn']


# TODO: Replace with published version of aws-test-harness under an alias?
def execute_state_machine(example_state_machine_arn: str, step_functions_client: SFNClient,
                          execution_input: Dict[str, Any]) -> DescribeExecutionOutputTypeDef:
    state_machine_execution_arn = start_state_machine_execution(example_state_machine_arn, step_functions_client,
                                                                execution_input)

    describe_execution_result = wait_for_value_matching(
        lambda: step_functions_client.describe_execution(executionArn=state_machine_execution_arn),
        'completed execution result',
        lambda execution_description: execution_description is not None and execution_description['status'] != 'RUNNING'
    )

    assert describe_execution_result is not None
    assert describe_execution_result.get('cause') is None
    assert describe_execution_result['status'] == 'SUCCEEDED'

    return describe_execution_result
