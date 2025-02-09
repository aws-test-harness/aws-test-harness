from logging import Logger

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}resource-registry-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack) -> None:
    test_stack.ensure_state_is(
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={})),
        Outputs=dict(BucketName=dict(Value=dict(Ref='Bucket')))
    )


def test_provides_physical_id_for_resource_specified_by_logical_id(test_stack: TestCloudFormationStack,
                                                                   boto_session: Session) -> None:
    bucket_name = test_stack.get_output_value('BucketName')
    resource_registry = ResourceRegistry(test_stack.name, boto_session)

    physical_id = resource_registry.get_physical_resource_id('Bucket')

    assert physical_id == bucket_name
