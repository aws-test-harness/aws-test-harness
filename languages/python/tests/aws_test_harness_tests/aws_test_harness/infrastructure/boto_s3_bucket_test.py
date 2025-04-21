from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.infrastructure.boto_s3_bucket import BotoS3Bucket
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}s3-bucket-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack) -> None:
    test_stack.ensure_state_is(
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={})),
        Outputs=dict(BucketName=dict(Value=dict(Ref='Bucket')))
    )


def test_saves_content_to_specified_object(test_stack: TestCloudFormationStack, boto_session: Session,
                                           s3_test_client: S3TestClient) -> None:
    bucket_name = test_stack.get_output_value('BucketName')

    s3_bucket = BotoS3Bucket(bucket_name, boto_session)
    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'

    s3_bucket.put_object(Key=object_key, Body=object_content)

    assert object_content == s3_test_client.get_object_content(bucket_name, object_key)
