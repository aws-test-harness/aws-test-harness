import json
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.test_harness import TestHarness
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient
from aws_test_harness_tests.support.step_functions_test_client import StepFunctionsTestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}test-harness-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack, test_double_macro_name: str) -> None:
    test_stack.ensure_state_is(
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


@pytest.fixture(scope="module")
def test_harness(test_stack: TestCloudFormationStack, logger: Logger, aws_profile: str) -> TestHarness:
    return TestHarness(test_stack.name, logger, aws_profile)


def test_provides_object_to_interact_with_state_machine_specified_by_cfn_resource_logical_id(
        test_harness: TestHarness) -> None:
    state_machine = test_harness.state_machine('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.status == 'SUCCEEDED'
    assert execution.output == '3'


def test_provides_object_for_interacting_with_test_doubles_that_do_not_execute_code(
        test_harness: TestHarness, test_stack: TestCloudFormationStack, s3_test_client: S3TestClient
) -> None:
    s3_bucket = test_harness.test_doubles.s3_bucket('Messages')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_stack_resource_physical_id('MessagesAWSTestHarnessS3Bucket')
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)


def test_provides_object_for_controlling_behaviour_of_test_doubles_that_execute_code(
        test_harness: TestHarness, test_stack: TestCloudFormationStack,
        step_functions_test_client: StepFunctionsTestClient,
) -> None:
    test_double_source = test_harness.test_doubles

    orange_test_double_state_machine = test_double_source.state_machine('Orange')
    expected_orange_result = dict(randomString=str(uuid4()))
    orange_test_double_state_machine.return_value = expected_orange_result

    blue_test_double_state_machine = test_double_source.state_machine('Blue')
    expected_blue_result = dict(randomString=str(uuid4()))
    blue_test_double_state_machine.return_value = expected_blue_result

    orange_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('OrangeAWSTestHarnessStateMachine'),
        {}
    )
    assert json.loads(orange_execution['output']) == expected_orange_result

    blue_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('BlueAWSTestHarnessStateMachine'),
        {}
    )
    assert json.loads(blue_execution['output']) == expected_blue_result
