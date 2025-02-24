import os.path
from logging import Logger

from boto3 import Session

from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


def test_managing_test_double_s3_buckets(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session,
                                         system_command_executor: SystemCommandExecutor,
                                         s3_deployment_assets_bucket_name: str) -> None:
    system_command_executor.execute([absolute_path_to('../../../scripts/build.sh')])

    system_command_executor.execute(
        [
            absolute_path_to('../../../build/install.sh'),
            f"{cfn_stack_name_prefix}infrastructure",
            s3_deployment_assets_bucket_name,
            'aws-test-harness/infrastructure/',
            'infrastructure-tests-'
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )

    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}acceptance', logger, boto_session)

    stack.ensure_state_is(
        Transform=['infrastructure-tests-AWSTestHarness-TestDoubles'],
        Parameters=dict(AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList')),
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={})),
        AWSTestHarnessS3Buckets='First,Second'
    )

    first_s3_bucket_resource = stack.get_stack_resource('FirstAWSTestHarnessS3Bucket')
    assert first_s3_bucket_resource is not None
    assert first_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    second_s3_bucket_resource = stack.get_stack_resource('SecondAWSTestHarnessS3Bucket')
    assert second_s3_bucket_resource is not None
    assert second_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'


def absolute_path_to(relative_file_path: str) -> str:
    test_double_template_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), relative_file_path))
    return test_double_template_file_path
