import json
from logging import Logger
from typing import Generator
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness import aws_test_harness, TestHarness
from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack, boto_session: Session,
               s3_deployment_assets_bucket_name: str, system_command_executor: SystemCommandExecutor,
               cfn_stack_name_prefix: str) -> None:
    system_command_executor.execute([
        absolute_path_relative_to(__file__, '..', 'infrastructure', 'scripts', 'build.sh')
    ])

    system_command_executor.execute(
        [
            absolute_path_relative_to(__file__, '..', 'infrastructure', 'build', 'install.sh'),
            f"{cfn_stack_name_prefix}infrastructure",
            s3_deployment_assets_bucket_name,
            'aws-test-harness/infrastructure/',
            'acceptance-tests-'
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )

    test_cloudformation_stack.ensure_state_is(
        AWSTemplateFormatVersion='2010-09-09',
        Transform=['acceptance-tests-AWSTestHarness-TestDoubles', 'AWS::Serverless-2016-10-31'],
        Parameters=dict(
            AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList'),
            AWSTestHarnessStateMachines=dict(Type='CommaDelimitedList'),
        ),
        Resources=dict(
            StateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition={
                        "StartAt": "GetObject",
                        "States": {
                            "GetObject": {
                                "Type": "Task",
                                "Parameters": {
                                    "Bucket": "${MessagesS3BucketName}",
                                    "Key.$": "$.s3ObjectKey"
                                },
                                "Resource": "arn:aws:states:::aws-sdk:s3:getObject",
                                "ResultSelector": {
                                    "result.$": "$.Body"
                                },
                                "ResultPath": "$.getObject",
                                "Next": "StartExecution"
                            },
                            "StartExecution": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::states:startExecution.sync:2",
                                "Parameters": {
                                    "StateMachineArn": "${RandomStringStateMachineArn}",
                                    "Input": {
                                        "StatePayload": "Hello from Step Functions!",
                                        "AWS_STEP_FUNCTIONS_STARTED_BY_EXECUTION_ID.$": "$$.Execution.Id"
                                    }
                                },
                                "ResultSelector": {
                                    "result.$": "$.Output"
                                },
                                "ResultPath": "$.startExecution",
                                "End": True
                            }
                        }
                    },
                    DefinitionSubstitutions=dict(
                        MessagesS3BucketName={'Ref': 'MessagesAWSTestHarnessS3Bucket'},
                        RandomStringStateMachineArn={'Ref': 'RandomStringAWSTestHarnessStateMachine'},
                    )
                ),
                Connectors=dict(
                    RandomStringStateMachineConnector=dict(
                        Properties=dict(
                            Destination=dict(Id='RandomStringAWSTestHarnessStateMachine'),
                            Permissions=['Read', 'Write']
                        )
                    ),
                    MessagesS3BucketConnector=dict(
                        Properties=dict(
                            Destination=dict(Id='MessagesAWSTestHarnessS3Bucket'),
                            Permissions=['Read']
                        )
                    )
                )
            ),
        ),
        AWSTestHarnessS3Buckets='Messages',
        AWSTestHarnessStateMachines='RandomString',
    )


@pytest.fixture(scope='function')
def test_harness(logger: Logger, aws_profile: str, test_cloudformation_stack: TestCloudFormationStack) -> Generator[
    TestHarness
]:
    test_harness = aws_test_harness(test_cloudformation_stack.name, aws_profile, logger)
    yield test_harness
    test_harness.tear_down()


def test_executing_a_step_function_that_interacts_with_test_doubles(test_harness: TestHarness) -> None:
    s3_object_key = str(uuid4())
    s3_object_content = f'Random content: {uuid4()}'
    messages_bucket = test_harness.twin_s3_bucket('Messages')
    messages_bucket.put_object(Key=s3_object_key, Body=s3_object_content)

    random_string = str(uuid4())
    test_harness.twin_state_machine('RandomString', lambda _: dict(randomString=random_string))

    state_machine = test_harness.state_machine('StateMachine')

    execution = state_machine.execute({'s3ObjectKey': s3_object_key})

    assert execution.status == 'SUCCEEDED', f'{execution.error}: {execution.cause}'
    assert execution.output is not None

    execution_output = json.loads(execution.output)

    assert 'getObject' in execution_output
    assert execution_output['getObject']['result'] == s3_object_content

    assert 'startExecution' in execution_output
    assert execution_output['startExecution']['result'] == dict(randomString=random_string)
