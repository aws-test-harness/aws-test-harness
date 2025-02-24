from logging import Logger
from typing import cast
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_s3 import S3Client

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_doubles_macro.test_double_s3_bucket_resource_factory import TestDoubleS3BucketResourceFactory


@pytest.fixture(scope="module")
def example_bucket_name(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> str:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-s3-bucket-resource-factory', logger,
                                    boto_session)
    resource_description = TestDoubleS3BucketResourceFactory.generate_resource()

    stack.ensure_state_is(Resources=dict(ExampleBucket=resource_description))
    example_bucket_resource = stack.get_stack_resource('ExampleBucket')
    assert example_bucket_resource is not None
    assert example_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    return example_bucket_resource['PhysicalResourceId']


@pytest.fixture(scope="module")
def s3_client(boto_session: Session) -> S3Client:
    return cast(S3Client, boto_session.client('s3'))


def test_generates_s3_bucket_cloudformation_resource(example_bucket_name: str, s3_client: S3Client) -> None:
    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_client.put_object(Bucket=example_bucket_name, Key=object_key, Body=object_content)
    retrieved_content = s3_client.get_object(Bucket=example_bucket_name, Key=object_key)['Body'].read().decode('utf-8')

    assert retrieved_content == object_content


def test_enables_bucket_encryption(example_bucket_name: str, s3_client: S3Client) -> None:
    bucket_encryption_configuration = s3_client.get_bucket_encryption(Bucket=example_bucket_name)

    assert len([
        rule for rule in bucket_encryption_configuration['ServerSideEncryptionConfiguration']['Rules']
        if rule.get('ApplyServerSideEncryptionByDefault', {})['SSEAlgorithm'] == 'AES256']
    ) == 1, 'Expected bucket to be encrypted with AES256'


def test_enables_object_expiration(example_bucket_name: str, s3_client: S3Client) -> None:
    bucket_lifecycle_configuration = s3_client.get_bucket_lifecycle_configuration(Bucket=example_bucket_name)

    assert len([
        rule for rule in bucket_lifecycle_configuration['Rules']
        if rule.get('Filter', {}).get('Prefix') == '' and rule.get('Expiration', {}).get('Days') == 1 and rule[
            'Status'] == 'Enabled'
    ]) == 1, 'Expected bucket to have a lifecycle rule that expires objects after 1 day'


def test_disables_object_versioning(example_bucket_name: str, s3_client: S3Client) -> None:
    versioning = s3_client.get_bucket_versioning(Bucket=example_bucket_name)
    assert versioning.get('Status', 'Suspended') == 'Suspended', 'Did not expect bucket versioning to be enabled'


def test_disables_public_access(example_bucket_name: str, s3_client: S3Client) -> None:
    get_public_access_block_result = s3_client.get_public_access_block(Bucket=example_bucket_name)
    public_access_block_configuration = get_public_access_block_result['PublicAccessBlockConfiguration']

    assert public_access_block_configuration.get('BlockPublicAcls', False), 'Expected BlockPublicAcls to be enabled'
    assert public_access_block_configuration.get('IgnorePublicAcls', False), 'Expected IgnorePublicAcls to be enabled'
    assert public_access_block_configuration.get('BlockPublicPolicy', False), 'Expected BlockPublicPolicy to be enabled'
    assert public_access_block_configuration.get('RestrictPublicBuckets',
                                                 False), 'Expected RestrictPublicBuckets to be enabled'
