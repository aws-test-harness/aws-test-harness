import json
from logging import Logger
from os import path
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.service_resource import S3ServiceResource

from aws_test_harness.step_functions.state_machine_source import StateMachineSource
from aws_test_harness.test_double_registry import TestDoubleRegistry
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
        logger: Logger, aws_profile: str, test_cfn_stack_name: str,
        test_cloudformation_stack: TestCloudFormationStack, boto_session: Session) -> None:
    test_double_source = TestDoubleRegistry(test_cfn_stack_name, aws_profile)
    messages_bucket_name = test_double_source.get_s3_bucket_name('Messages')

    s3_resource: S3ServiceResource = boto_session.resource('s3')
    s3_bucket = s3_resource.Bucket(messages_bucket_name)

    s3_object_key = str(uuid4())
    s3_object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=s3_object_key, Body=s3_object_content)

    state_machine_source = StateMachineSource(test_cfn_stack_name, logger, aws_profile)
    state_machine = state_machine_source.get_state_machine('StateMachine')

    execution = state_machine.execute({'s3ObjectKey': s3_object_key})

    assert execution.status == 'SUCCEEDED'

    assert execution.output is not None
    assert json.loads(execution.output) == {"result": s3_object_content}
