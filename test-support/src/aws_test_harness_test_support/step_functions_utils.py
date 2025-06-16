import json
from typing import Dict, Any

from mypy_boto3_stepfunctions.client import SFNClient
from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef

from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching


def start_state_machine_execution(example_state_machine_arn: str, step_functions_client: SFNClient,
                                  execution_input: Dict[str, Any]) -> str:
    start_execution_result = step_functions_client.start_execution(
        stateMachineArn=example_state_machine_arn,
        input=json.dumps(execution_input)
    )

    return start_execution_result['executionArn']


def wait_for_state_machine_execution_completion(state_machine_execution_arn: str,
                                                step_functions_client: SFNClient) -> DescribeExecutionOutputTypeDef:
    describe_execution_result = wait_for_value_matching(
        lambda: step_functions_client.describe_execution(executionArn=state_machine_execution_arn),
        'completed execution result',
        lambda execution_description: execution_description is not None and execution_description['status'] != 'RUNNING'
    )

    assert describe_execution_result is not None
    return describe_execution_result


# TODO: Replace with published version of aws-test-harness under an alias?
def execute_state_machine(state_machine_arn: str, step_functions_client: SFNClient,
                          execution_input: Dict[str, Any]) -> DescribeExecutionOutputTypeDef:
    state_machine_execution_arn = start_state_machine_execution(state_machine_arn, step_functions_client,
                                                                execution_input)

    return wait_for_state_machine_execution_completion(state_machine_execution_arn, step_functions_client)


def assert_describes_successful_execution(execution_description: DescribeExecutionOutputTypeDef) -> None:
    failure_cause = execution_description.get('cause')
    assert failure_cause is None, f"State machine execution failed with cause: {failure_cause}"
    assert execution_description['status'] == 'SUCCEEDED'


def assert_describes_failed_execution(execution_description: DescribeExecutionOutputTypeDef,
                                      expected_cause: str, expected_error: str) -> None:
    assert execution_description['status'] == 'FAILED', \
        f"State machine execution did not fail, status: '{execution_description['status']}'"

    actual_error = execution_description.get('error')
    actual_cause = execution_description.get('cause')

    assert actual_error == expected_error, \
        (f"State machine execution failed with unexpected error: '{actual_error}', expected: '{expected_error}'. "
         f"Cause was: '{actual_cause}'")

    assert actual_cause == expected_cause, \
        f"State machine execution failed with unexpected cause: '{actual_cause}', expected: '{expected_cause}'"
