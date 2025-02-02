from logging import Logger
from unittest.mock import Mock
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_s3.client import S3Client

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.test_double_source import TestDoubleSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-source-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack, test_doubles_template_path: str) -> None:
    test_stack.ensure_state_matches_yaml_template_file(
        test_doubles_template_path,
        S3BucketNames='First,Second'
    )


def test_provides_object_to_interract_with_test_double_s3_bucket(test_stack: TestCloudFormationStack,
                                                                 boto_session: Session) -> None:
    def create_test_double_resource_registry() -> ResourceRegistry:
        resource_registry = Mock(spec=ResourceRegistry)
        resource_registry.get_physical_resource_id.side_effect = (
            lambda logical_id: test_stack.get_output_value(f'{logical_id}Name')
        )
        return resource_registry

    test_double_source = TestDoubleSource(create_test_double_resource_registry, boto_session)

    s3_bucket = test_double_source.s3_bucket('First')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_output_value('FirstS3BucketName')
    assert object_content_at_s3_location(first_s3_bucket_name, object_key, boto_session) == object_content


# TODO: Extract test helper
def object_content_at_s3_location(bucket_name: str, object_key: str, boto_session: Session) -> str:
    s3_client: S3Client = boto_session.client('s3')
    get_object_result = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    streaming_body = get_object_result['Body']

    return streaming_body.read().decode('utf-8')
