from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.cloudformation_resource_registry import CloudFormationResourceRegistry
from aws_test_harness.infrastructure.boto_aws_resource_factory import BotoAwsResourceFactory
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}boto-aws-resource-factory-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack) -> None:
    test_stack.ensure_state_is(
        Resources=dict(
            Bucket=dict(
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
                            dict(ServerSideEncryptionByDefault=dict(SSEAlgorithm='AES256'))
                        ]
                    ),
                    LifecycleConfiguration=dict(Rules=[dict(Status='Enabled', ExpirationInDays=1)])
                )
            )
        )
    )


def test_provides_object_for_interacting_with_specified_s3_bucket_in_cfn_stack(
        test_stack: TestCloudFormationStack, boto_session: Session, s3_test_client: S3TestClient
):
    aws_resource_factory = BotoAwsResourceFactory(
        boto_session,
        CloudFormationResourceRegistry(test_stack.name, boto_session)
    )

    s3_bucket = aws_resource_factory.get_s3_bucket('Bucket')

    s3_key = str(uuid4())
    object_body = str(uuid4())
    s3_bucket.put_object(Key=s3_key, Body=object_body)

    bucket_name = test_stack.get_stack_resource_physical_id('Bucket')
    content_at_key = s3_test_client.get_object_content(bucket_name, s3_key)
    assert content_at_key == object_body
