from logging import Logger

from boto3 import Session

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_doubles_macro.test_double_resource_factory import TestDoubleResourceFactory


def test_generates_s3_bucket_cloudformation_resource_for_each_specified_bucket_id() -> None:
    desired_test_doubles = dict(AWSTestHarnessS3Buckets=['First', 'Second'])

    resources = TestDoubleResourceFactory.generate_additional_resources(desired_test_doubles)

    assert len(resources) == 2
    assert 'FirstAWSTestHarnessS3Bucket' in resources
    assert 'SecondAWSTestHarnessS3Bucket' in resources


def test_generates_s3_bucket_cloudformation_resources(cfn_stack_name_prefix: str, logger: Logger,
                                                      boto_session: Session) -> None:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-resource-factory', logger, boto_session)
    desired_test_doubles = dict(AWSTestHarnessS3Buckets=['Example'])

    resources = TestDoubleResourceFactory.generate_additional_resources(desired_test_doubles)

    stack.ensure_state_is(Resources=dict(ExampleAWSTestHarnessS3Bucket=resources['ExampleAWSTestHarnessS3Bucket']))
    example_s3_bucket_resource = stack.get_stack_resource('ExampleAWSTestHarnessS3Bucket')
    assert example_s3_bucket_resource is not None
    assert example_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'
