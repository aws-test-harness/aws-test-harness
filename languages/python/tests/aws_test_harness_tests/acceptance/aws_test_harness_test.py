import json
from logging import Logger
from typing import Generator
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness import aws_test_harness, TestHarness
from aws_test_harness.domain.state_machine_execution_failure import StateMachineExecutionFailure
from aws_test_harness_test_support.step_functions_utils import assert_describes_successful_execution, \
    assert_describes_failed_execution
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient
from aws_test_harness_tests.support.step_functions_test_client import StepFunctionsTestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, test_double_macro_name: str, boto_session: Session,
               logger: Logger) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-harness-test', logger, boto_session)

    stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31', test_double_macro_name],
        Parameters=dict(
            AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList'),
            AWSTestHarnessStateMachines=dict(Type='CommaDelimitedList'),
        ),
        Resources=dict(
            AddNumbersStateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition=dict(
                        StartAt='SetResult',
                        States=dict(
                            SetResult=dict(
                                Type='Pass',
                                Parameters={'result.$': 'States.MathAdd($.firstNumber, $.secondNumber)'},
                                OutputPath='$.result',
                                End=True
                            )
                        )
                    )
                )
            )
        ),
        AWSTestHarnessS3Buckets='Messages',
        AWSTestHarnessStateMachines='Orange,Blue'
    )

    return stack


@pytest.fixture(scope="function")
def test_harness(test_stack: TestCloudFormationStack, logger: Logger, aws_profile: str) -> Generator[TestHarness]:
    test_harness = aws_test_harness(test_stack.name, aws_profile, logger)
    yield test_harness
    test_harness.tear_down()


def test_executing_state_machine_specified_by_cfn_resource_logical_id(
        test_harness: TestHarness) -> None:
    state_machine = test_harness.state_machine('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.status == 'SUCCEEDED'
    assert execution.output == '3'


def test_interacting_with_test_s3_bucket(
        test_harness: TestHarness, test_stack: TestCloudFormationStack, s3_test_client: S3TestClient
) -> None:
    s3_bucket = test_harness.test_s3_bucket('Messages')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_stack_resource_physical_id('MessagesAWSTestHarnessS3Bucket')
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)


def test_using_twin_to_control_state_machine_output(
        test_harness: TestHarness, test_stack: TestCloudFormationStack,
        step_functions_test_client: StepFunctionsTestClient,
) -> None:
    orange_state_machine = test_harness.twin_state_machine(
        'Orange',
        lambda execution_input: dict(orangeString=execution_input['randomString'])
    )

    blue_state_machine = test_harness.twin_state_machine(
        'Blue',
        lambda execution_input: dict(blueString=execution_input['randomString'])
    )

    orange_random_string = str(uuid4())
    orange_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('OrangeAWSTestHarnessStateMachine'),
        dict(randomString=orange_random_string)
    )
    assert_describes_successful_execution(orange_execution)
    assert orange_state_machine.invocation_count == 1
    assert orange_state_machine.invocations[0][0] == dict(randomString=orange_random_string)
    assert json.loads(orange_execution['output']) == dict(orangeString=orange_random_string)

    blue_random_string = str(uuid4())
    blue_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('BlueAWSTestHarnessStateMachine'),
        dict(randomString=blue_random_string)
    )
    assert_describes_successful_execution(blue_execution)
    assert blue_state_machine.invocation_count == 1
    assert blue_state_machine.invocations[0][0] == dict(randomString=blue_random_string)
    assert json.loads(blue_execution['output']) == dict(blueString=blue_random_string)


def test_using_twin_to_drive_state_machine_error(
        test_harness: TestHarness, test_stack: TestCloudFormationStack,
        step_functions_test_client: StepFunctionsTestClient,
) -> None:
    test_harness.twin_state_machine(
        'Orange',
        lambda _: StateMachineExecutionFailure(cause='the expected cause', error='TheExpectedError')
    )

    execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('OrangeAWSTestHarnessStateMachine'),
        dict()
    )
    assert_describes_failed_execution(execution, 'the expected cause', 'TheExpectedError')


def test_ignoring_state_machine_invocations_after_being_torn_down(
        test_harness: TestHarness, test_stack: TestCloudFormationStack,
        step_functions_test_client: StepFunctionsTestClient) -> None:
    test_double_state_machine = test_harness.twin_state_machine('Orange')

    state_machine_arn = test_stack.get_stack_resource_physical_id('OrangeAWSTestHarnessStateMachine')

    first_execution_description = step_functions_test_client.execute_state_machine(state_machine_arn, {})
    assert_describes_successful_execution(first_execution_description)
    call_count_before_teardown = test_double_state_machine.invocation_count
    assert call_count_before_teardown == 1

    test_harness.tear_down()

    step_functions_test_client.execute_state_machine(state_machine_arn, {})
    assert test_double_state_machine.invocation_count == call_count_before_teardown
