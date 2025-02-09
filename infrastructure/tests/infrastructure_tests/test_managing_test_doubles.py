import os.path
from logging import Logger
from uuid import uuid4

from boto3 import Session
from mypy_boto3_s3.client import S3Client

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


def test_managing_test_double_s3_buckets(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> None:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}infrastructure-acceptance-tests', logger, boto_session)
    test_double_template_file_path = absolute_file_path('../../templates/test-doubles.yaml')

    stack.ensure_state_matches_yaml_template_file(test_double_template_file_path, S3BucketNames='First,Second')

    first_s3_bucket_resource = stack.get_stack_resource('FirstS3Bucket')
    assert first_s3_bucket_resource is not None
    assert first_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    second_s3_bucket_resource = stack.get_stack_resource('SecondS3Bucket')
    assert second_s3_bucket_resource is not None
    assert second_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_client: S3Client = boto_session.client('s3')
    second_bucket_name = second_s3_bucket_resource['PhysicalResourceId']
    s3_client.put_object(Bucket=second_bucket_name, Key=object_key, Body=object_content)
    retrieved_content = s3_client.get_object(Bucket=second_bucket_name, Key=object_key)['Body'].read().decode('utf-8')

    assert retrieved_content == object_content

    bucket_encryption_configuration = s3_client.get_bucket_encryption(Bucket=second_bucket_name)

    assert len([
        rule for rule in bucket_encryption_configuration['ServerSideEncryptionConfiguration']['Rules']
        if rule.get('ApplyServerSideEncryptionByDefault', {})['SSEAlgorithm'] == 'AES256']
    ) == 1, 'Expected bucket to be encrypted with AES256'

    bucket_lifecycle_configuration = s3_client.get_bucket_lifecycle_configuration(Bucket=second_bucket_name)

    assert len([
        rule for rule in bucket_lifecycle_configuration['Rules']
        if rule.get('Filter', {}).get('Prefix') == '' and rule.get('Expiration', {}).get('Days') == 1 and rule[
            'Status'] == 'Enabled'
    ]) == 1, 'Expected bucket to have a lifecycle rule that expires objects after 1 day'

    versioning = s3_client.get_bucket_versioning(Bucket=second_bucket_name)
    assert versioning.get('Status', 'Suspended') == 'Suspended', 'Did not expect bucket versioning to be enabled'

    public_access_block_configuration = s3_client.get_public_access_block(Bucket=second_bucket_name)[
        'PublicAccessBlockConfiguration'
    ]
    assert public_access_block_configuration.get('BlockPublicAcls', False), 'Expected BlockPublicAcls to be enabled'
    assert public_access_block_configuration.get('IgnorePublicAcls', False), 'Expected IgnorePublicAcls to be enabled'
    assert public_access_block_configuration.get('BlockPublicPolicy', False), 'Expected BlockPublicPolicy to be enabled'
    assert public_access_block_configuration.get('RestrictPublicBuckets',
                                                 False), 'Expected RestrictPublicBuckets to be enabled'


def absolute_file_path(relative_file_path: str) -> str:
    test_double_template_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), relative_file_path))
    return test_double_template_file_path
