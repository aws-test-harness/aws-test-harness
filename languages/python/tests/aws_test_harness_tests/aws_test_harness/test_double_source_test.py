from logging import Logger
from unittest.mock import Mock
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.test_double_source import TestDoubleSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-source-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack, test_double_macro_name: str) -> None:
    test_stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31', test_double_macro_name],
        Parameters=dict(AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList')),
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={})),
        AWSTestHarnessS3Buckets='First,Second',
        Outputs=dict(
            FirstAWSTestHarnessS3BucketName=dict(Value={'Ref': 'FirstAWSTestHarnessS3Bucket'}),
            SecondAWSTestHarnessS3BucketName=dict(Value={'Ref': 'SecondAWSTestHarnessS3Bucket'})
        )
    )


def test_provides_object_to_interract_with_test_double_s3_bucket(
        test_stack: TestCloudFormationStack, boto_session: Session, s3_test_client: S3TestClient
) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id.side_effect = (
        lambda logical_id: test_stack.get_output_value(f'{logical_id}Name')
    )

    test_double_source = TestDoubleSource(resource_registry, boto_session)

    s3_bucket = test_double_source.s3_bucket('First')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_output_value('FirstAWSTestHarnessS3BucketName')
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)
