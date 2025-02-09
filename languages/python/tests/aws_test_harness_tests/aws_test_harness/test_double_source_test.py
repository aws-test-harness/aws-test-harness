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
def before_all(test_stack: TestCloudFormationStack, test_doubles_template_path: str) -> None:
    test_stack.ensure_state_matches_yaml_template_file(
        test_doubles_template_path,
        S3BucketNames='First,Second'
    )


def test_provides_object_to_interract_with_test_double_s3_bucket(
        test_stack: TestCloudFormationStack, boto_session: Session, s3_test_client: S3TestClient
) -> None:
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
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)
