from logging import Logger
from unittest.mock import Mock
from uuid import uuid4

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.test_double_source import TestDoubleSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


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


def test_provides_object_to_interract_with_test_double_s3_bucket(
        boto_session: Session, logger: Logger, test_stack: TestCloudFormationStack, s3_test_client: S3TestClient
) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id.side_effect = (
        lambda logical_id: test_stack.get_stack_resource_physical_id(logical_id)
    )

    test_double_source = TestDoubleSource(resource_registry, Mock(InvocationPostOffice), Mock(RepeatingTaskScheduler),
                                          boto_session, logger)

    s3_bucket = test_double_source.s3_bucket('Red')

    object_key = str(uuid4())
    object_content = f'Random content: {uuid4()}'
    s3_bucket.put_object(Key=object_key, Body=object_content)

    first_s3_bucket_name = test_stack.get_stack_resource_physical_id('RedAWSTestHarnessS3Bucket')
    assert object_content == s3_test_client.get_object_content(first_s3_bucket_name, object_key)


def test_provides_mock_to_control_test_double_state_machine(boto_session: Session, logger: Logger) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id = lambda logical_id: logical_id + 'Arn'

    invocation_handler_repeating_task_scheduler = Mock(spec=RepeatingTaskScheduler)
    invocation_handler_repeating_task_scheduler.scheduled.return_value = False

    invocation_post_office = Mock(spec=InvocationPostOffice)
    invocation_post_office.maybe_collect_invocation.return_value = Invocation(
        target='OrangeAWSTestHarnessStateMachineArn',
        id='123456789'
    )

    test_double_source = TestDoubleSource(resource_registry, invocation_post_office,
                                          invocation_handler_repeating_task_scheduler,
                                          boto_session, logger)

    test_double_state_machine = test_double_source.state_machine('Orange')
    test_double_state_machine.return_value = dict(message='result message')

    invocation_handler_repeating_task_scheduler.schedule.assert_called()
    scheduled_task = invocation_handler_repeating_task_scheduler.schedule.call_args[0][0]
    scheduled_task()

    invocation_post_office.post_result.assert_called_once_with('123456789', dict(value=dict(message='result message')))


def test_does_not_schedule_invocation_handler_repeating_task_if_already_scheduled(
        boto_session: Session, logger: Logger
) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id = lambda logical_id: 'any arn'

    invocation_handler_repeating_task_scheduler = Mock(spec=RepeatingTaskScheduler)
    invocation_handler_repeating_task_scheduler.scheduled.return_value = True

    test_double_source = TestDoubleSource(resource_registry, Mock(spec=InvocationPostOffice),
                                          invocation_handler_repeating_task_scheduler,
                                          boto_session, logger)

    test_double_source.state_machine('any identifier')

    invocation_handler_repeating_task_scheduler.schedule.assert_not_called()
