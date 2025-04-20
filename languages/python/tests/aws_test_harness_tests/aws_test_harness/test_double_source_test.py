import json
from logging import Logger
from unittest.mock import Mock
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.infrastructure.serverless_invocation_post_office import ServerlessInvocationPostOffice
from aws_test_harness.infrastructure.thread_based_repeating_task_scheduler import ThreadBasedRepeatingTaskScheduler
from aws_test_harness.test_double_source import TestDoubleSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient
from aws_test_harness_tests.support.step_functions_test_client import StepFunctionsTestClient


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger,
               test_double_macro_name: str) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-source-test', logger, boto_session)

    stack.ensure_state_is(
        Transform=[test_double_macro_name],
        Parameters=dict(
            AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList'),
            AWSTestHarnessStateMachines=dict(Type='CommaDelimitedList'),
        ),
        Resources=dict(),
        AWSTestHarnessS3Buckets='Red',
        AWSTestHarnessStateMachines='Orange,Blue',
    )

    return stack


@pytest.fixture(scope='function')
def resource_registry(test_stack: TestCloudFormationStack, boto_session: Session, logger: Logger) -> TestDoubleSource:
    resource_registry_mock = Mock(spec=ResourceRegistry)
    resource_registry_mock.get_physical_resource_id.side_effect = (
        lambda logical_id: test_stack.get_stack_resource_physical_id(logical_id)
    )
    return resource_registry_mock


def test_provides_object_to_interract_with_test_double_s3_bucket(
        resource_registry: ResourceRegistry, boto_session: Session, logger: Logger, test_stack: TestCloudFormationStack,
        s3_test_client: S3TestClient
) -> None:
    test_double_source = TestDoubleSource(resource_registry, boto_session, logger,
                                          ServerlessInvocationPostOffice(
                                              resource_registry.get_physical_resource_id(
                                                  'AWSTestHarnessTestDoubleInvocationQueue'),
                                              resource_registry.get_physical_resource_id(
                                                  'AWSTestHarnessTestDoubleInvocationTable'), boto_session, logger),
                                          ThreadBasedRepeatingTaskScheduler(logger))

    s3_bucket = test_double_source.s3_bucket('Red')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_stack_resource_physical_id('RedAWSTestHarnessS3Bucket')
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)


def test_provides_mocks_to_control_test_double_state_machines(
        resource_registry: ResourceRegistry, boto_session: Session, logger: Logger, test_stack: TestCloudFormationStack,
        step_functions_test_client: StepFunctionsTestClient,
) -> None:
    test_double_source = TestDoubleSource(resource_registry, boto_session, logger,
                                          ServerlessInvocationPostOffice(
                                              resource_registry.get_physical_resource_id(
                                                  'AWSTestHarnessTestDoubleInvocationQueue'),
                                              resource_registry.get_physical_resource_id(
                                                  'AWSTestHarnessTestDoubleInvocationTable'), boto_session, logger),
                                          ThreadBasedRepeatingTaskScheduler(logger))

    orange_test_double_state_machine = test_double_source.state_machine('Orange')
    expected_orange_result = dict(randomString=str(uuid4()))
    orange_test_double_state_machine.return_value = expected_orange_result

    blue_test_double_state_machine = test_double_source.state_machine('Blue')
    expected_blue_result = dict(randomString=str(uuid4()))
    blue_test_double_state_machine.return_value = expected_blue_result

    orange_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('OrangeAWSTestHarnessStateMachine'),
        {}
    )
    assert json.loads(orange_execution['output']) == expected_orange_result

    blue_execution = step_functions_test_client.execute_state_machine(
        test_stack.get_stack_resource_physical_id('BlueAWSTestHarnessStateMachine'),
        {}
    )
    assert json.loads(blue_execution['output']) == expected_blue_result

# def test_uses_same_invocation_listener_for_all_test_doubles(boto_session: Session, logger: Logger) -> None:
#     invocation_listener: Mock = Mock(spec=InvocationListener)
#     resource_registry = Mock(spec=ResourceRegistry)
#     test_double_source = TestDoubleSource(resource_registry, boto_session, logger, lambda: invocation_listener)
#
#     test_double_source.state_machine('Orange')
#     test_double_source.state_machine('Blue')
#
#     invocation_listener.listen.assert_called_once()
