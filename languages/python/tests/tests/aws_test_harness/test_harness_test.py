import os.path
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.test_harness import TestHarness
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}test-harness-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack, infrastructure_directory_path: str,
               test_doubles_template_file_name: str, cfn_stack_name_prefix: str,
               boto_session: Session, logger: Logger, system_command_executor: SystemCommandExecutor) -> None:
    templates_stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-harness-test-templates', logger,
                                              boto_session)

    templates_stack.ensure_state_is(
        AWSTemplateFormatVersion='2010-09-09',
        Resources=dict(
            Templates=dict(
                Type='AWS::S3::Bucket',
                Properties=dict(
                    PublicAccessBlockConfiguration=dict(
                        BlockPublicAcls=True,
                        BlockPublicPolicy=True,
                        IgnorePublicAcls=True,
                        RestrictPublicBuckets=True
                    ),
                    BucketEncryption=dict(
                        ServerSideEncryptionConfiguration=[
                            dict(
                                ServerSideEncryptionByDefault=dict(SSEAlgorithm='AES256')
                            )
                        ]
                    )
                )
            )
        ),
        Outputs=dict(
            TemplatesBucketName=dict(Value={'Ref': 'Templates'}),
            # Regional domain name avoids the need to wait for global propagation of the bucket name
            TemplatesBucketRegionalDomainName=dict(Value={'Fn::GetAtt': 'Templates.RegionalDomainName'})
        )
    )

    system_command_executor.execute(
        [
            os.path.normpath(os.path.join(infrastructure_directory_path, 'scripts/install.sh')),
            f's3://{templates_stack.get_output_value('TemplatesBucketName')}'
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )

    test_stack.ensure_state_is(
        Transform='AWS::Serverless-2016-10-31',
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
            ),
            TestDoubles=dict(
                Type='AWS::CloudFormation::Stack',
                Properties=dict(
                    Parameters=dict(S3BucketNames='Messages'),
                    TemplateURL=f'https://{templates_stack.get_output_value('TemplatesBucketRegionalDomainName')}/{test_doubles_template_file_name}'
                )
            )
        ),
        Outputs=dict(
            AddNumbersStateMachineArn=dict(Value=dict(Ref='AddNumbersStateMachine')),
            MessagesS3BucketName=dict(Value={'Fn::GetAtt': 'TestDoubles.Outputs.MessagesS3BucketName'}),
        )
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
