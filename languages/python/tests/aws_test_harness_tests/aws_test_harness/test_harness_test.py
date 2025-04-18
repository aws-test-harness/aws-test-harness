from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.test_harness import TestHarness
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}test-harness-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack, test_double_macro_name: str) -> None:
    test_stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31', test_double_macro_name],
        Parameters=dict(AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList')),
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
        Outputs=dict(
            AddNumbersStateMachineArn=dict(Value=dict(Ref='AddNumbersStateMachine')),
            MessagesS3BucketName=dict(Value={'Ref': 'MessagesAWSTestHarnessS3Bucket'}),
        ),
        AWSTestHarnessS3Buckets='Messages'
    )


def test_provides_object_to_interact_with_state_machine_specified_by_cfn_resource_logical_id(
        test_stack: TestCloudFormationStack, logger: Logger, aws_profile: str
) -> None:
    test_harness = TestHarness(test_stack.name, logger, aws_profile)

    state_machine = test_harness.state_machine('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.status == 'SUCCEEDED'
    assert execution.output == '3'


def test_provides_object_to_interract_with_test_double_specified_by_name(
        test_stack: TestCloudFormationStack, logger: Logger, aws_profile: str, s3_test_client: S3TestClient) -> None:
    test_harness = TestHarness(test_stack.name, logger, aws_profile)

    s3_bucket = test_harness.test_doubles.s3_bucket('Messages')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    messages_s3_bucket_name = test_stack.get_output_value('MessagesS3BucketName')
    assert object_content == s3_test_client.get_object_content(messages_s3_bucket_name, object_key)
