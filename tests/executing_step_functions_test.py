import json
from logging import Logger
from os import path
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.test_harness import TestHarness
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack, boto_session: Session,
               test_templates_s3_bucket_name: str, test_templates_s3_regional_domain_name: str,
               system_command_executor: SystemCommandExecutor) -> None:
    test_doubles_template_s3_prefix = 'aws-test-harness/templates'

    system_command_executor.execute(
        [
            absolute_path_to('../infrastructure/scripts/install.sh'),
            f's3://{test_templates_s3_bucket_name}/{test_doubles_template_s3_prefix}'
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )

    test_cloudformation_stack.ensure_state_is(
        AWSTemplateFormatVersion='2010-09-09',
        Transform='AWS::Serverless-2016-10-31',
        Resources=dict(
            StateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition=({
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
                                "End": True
                            }
                        }
                    }),
                    DefinitionSubstitutions=dict(
                        MessagesS3BucketName={'Fn::GetAtt': 'TestDoubles.Outputs.MessagesS3BucketName'}
                    ),
                    Policies=dict(
                        S3ReadPolicy=dict(BucketName={'Fn::GetAtt': 'TestDoubles.Outputs.MessagesS3BucketName'})
                    )
                )
            ),
            TestDoubles=dict(
                Type='AWS::CloudFormation::Stack',
                Properties=dict(
                    Parameters=dict(S3BucketNames='Messages'),
                    TemplateURL=f'https://{test_templates_s3_regional_domain_name}/{test_doubles_template_s3_prefix}/test-doubles.yaml'
                )
            )
        )
    )


def test_executing_a_step_function_that_interacts_with_test_doubles(
        logger: Logger, aws_profile: str, test_cfn_stack_name: str, boto_session: Session) -> None:
    test_harness = TestHarness(test_cfn_stack_name, logger, aws_profile)

    s3_object_key = str(uuid4())
    s3_object_content = f'Random content: {uuid4()}'

    messages_bucket = test_harness.test_doubles.s3_bucket('Messages')
    messages_bucket.put_object(Key=s3_object_key, Body=s3_object_content)

    state_machine = test_harness.state_machine('StateMachine')

    execution = state_machine.execute({'s3ObjectKey': s3_object_key})

    assert execution.status == 'SUCCEEDED'
    assert execution.output is not None
    assert json.loads(execution.output) == {"result": s3_object_content}


def absolute_path_to(relative_path: str) -> str:
    return path.normpath(path.join(path.dirname(__file__), relative_path))
