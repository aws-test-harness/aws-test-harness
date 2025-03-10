import json
from time import sleep, time
from typing import Optional

from mypy_boto3_stepfunctions.type_defs import DescribeExecutionOutputTypeDef


def start_state_machine_execution(example_state_machine_arn, step_functions_client, execution_input):
    start_execution_result = step_functions_client.start_execution(
        stateMachineArn=example_state_machine_arn,
        input=json.dumps(execution_input)
    )

    return start_execution_result['executionArn']


# TODO: Replace with published version of aws-test-harness under an alias?
def execute_state_machine(example_state_machine_arn, step_functions_client, execution_input):
    state_machine_execution_arn = start_state_machine_execution(example_state_machine_arn, step_functions_client,
                                                                execution_input)

    timeout_milliseconds = 5 * 1000
    expiry_time = get_epoch_milliseconds() + timeout_milliseconds

    describe_execution_result: Optional[DescribeExecutionOutputTypeDef] = None

    while get_epoch_milliseconds() < expiry_time:
        describe_execution_result = step_functions_client.describe_execution(executionArn=state_machine_execution_arn)

        if describe_execution_result['status'] == 'RUNNING':
            sleep(0.1)

    assert describe_execution_result is not None
    assert describe_execution_result.get('cause') is None
    assert describe_execution_result['status'] == 'SUCCEEDED'

    return describe_execution_result


def get_epoch_milliseconds():
    return int(round(time() * 1000))
