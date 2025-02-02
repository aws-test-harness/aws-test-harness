import json
from logging import Logger
from os import path
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_s3.client import S3Client

from aws_test_harness.test_harness import TestHarness
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack, boto_session: Session,
               test_templates_s3_bucket_name: str, test_templates_s3_regional_domain_name: str) -> None:
    # TODO: Replace with install script
    s3_client: S3Client = boto_session.client('s3')
    test_doubles_template_s3_key = 'aws-test-harness/templates/test-doubles.yaml'
    s3_client.upload_file(
        Filename=path.join(path.dirname(__file__), '../infrastructure/test-doubles.yaml'),
        Bucket=test_templates_s3_bucket_name,
        Key=test_doubles_template_s3_key
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
                    TemplateURL=f'https://{test_templates_s3_regional_domain_name}/{test_doubles_template_s3_key}'
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
