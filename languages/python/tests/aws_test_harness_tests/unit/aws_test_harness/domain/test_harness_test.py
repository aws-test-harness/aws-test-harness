import pytest

from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.domain.repeating_task_scheduler import RepeatingTaskScheduler
from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException
from aws_test_harness import TestHarness
from aws_test_harness_test_support.mocking import mock_class, when_calling, verify, inspect
from aws_test_harness_tests.support.builders.invocation_builder import an_invocation_with


@pytest.fixture(scope='function')
def aws_resource_registry() -> AwsResourceRegistry:
    return mock_class(AwsResourceRegistry)


@pytest.fixture(scope='function')
def aws_resource_factory() -> AwsResourceFactory:
    return mock_class(AwsResourceFactory)


@pytest.fixture(scope='function')
def invocation_handler_repeating_task_scheduler() -> RepeatingTaskScheduler:
    return mock_class(RepeatingTaskScheduler)


@pytest.fixture(scope='function')
def invocation_post_office() -> InvocationPostOffice:
    return mock_class(InvocationPostOffice)


@pytest.fixture(scope='function')
def test_harness(aws_resource_registry: AwsResourceRegistry, invocation_post_office: InvocationPostOffice,
                 invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
                 aws_resource_factory: AwsResourceFactory) -> TestHarness:
    return TestHarness(aws_resource_registry, invocation_post_office, invocation_handler_repeating_task_scheduler,
                       aws_resource_factory)


def test_provides_object_to_interact_with_test_s3_bucket(test_harness: TestHarness,
                                                                aws_resource_factory: AwsResourceFactory) -> None:
    the_s3_bucket = mock_class(S3Bucket)
    when_calling(aws_resource_factory.get_s3_bucket).invoke(
        lambda name: the_s3_bucket if name == 'MyBucketAWSTestHarnessS3Bucket' else None
    )

    provided_s3_bucket = test_harness.test_s3_bucket('MyBucket')

    assert provided_s3_bucket == the_s3_bucket


def test_provides_object_to_control_test_double_state_machine(
        test_harness: TestHarness, aws_resource_registry: AwsResourceRegistry,
        invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
        invocation_post_office: InvocationPostOffice
) -> None:
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: resource_id + 'ARN')
    when_calling(invocation_handler_repeating_task_scheduler.scheduled).always_return(False)
    when_calling(invocation_post_office.maybe_collect_invocation).always_return(
        an_invocation_with(target='OrangeAWSTestHarnessStateMachineARN', invocation_id='123456789')
    )

    test_harness.twin_state_machine(
        'Orange',
        lambda _: dict(message='result message')
    )

    verify(invocation_handler_repeating_task_scheduler.schedule).was_called()
    scheduled_task = inspect(invocation_handler_repeating_task_scheduler.schedule).call_args[0][0]
    scheduled_task()

    verify(invocation_post_office.post_result).was_called_once_with(
        invocation_id='123456789',
        result=dict(value=dict(message='result message'))
    )


def test_uses_default_test_double_state_machine_execution_handler_if_none_provided(
        test_harness: TestHarness, aws_resource_registry: AwsResourceRegistry,
        invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
        invocation_post_office: InvocationPostOffice
) -> None:
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: resource_id + 'ARN')
    when_calling(invocation_handler_repeating_task_scheduler.scheduled).always_return(False)
    when_calling(invocation_post_office.maybe_collect_invocation).always_return(
        an_invocation_with(target='OrangeAWSTestHarnessStateMachineARN', invocation_id='123456789')
    )

    test_harness.twin_state_machine('Orange')

    verify(invocation_handler_repeating_task_scheduler.schedule).was_called()
    scheduled_task = inspect(invocation_handler_repeating_task_scheduler.schedule).call_args[0][0]
    scheduled_task()

    verify(invocation_post_office.post_result).was_called_once_with(
        invocation_id='123456789',
        result=dict(value=dict())
    )


def test_does_not_schedule_invocation_handler_repeating_task_if_already_scheduled(
        test_harness: TestHarness, aws_resource_registry: AwsResourceRegistry,
        invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
        invocation_post_office: InvocationPostOffice) -> None:
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: 'any-arn')
    when_calling(invocation_handler_repeating_task_scheduler.scheduled).always_return(True)

    test_harness.twin_state_machine('any identifier')

    verify(invocation_handler_repeating_task_scheduler.schedule).was_not_called()


def test_resets_repeating_task_scheduler_when_asked_to_tear_down(
        test_harness: TestHarness, aws_resource_registry: AwsResourceRegistry,
        invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
        invocation_post_office: InvocationPostOffice
) -> None:
    test_harness.tear_down()

    verify(invocation_handler_repeating_task_scheduler.reset_schedule).was_called()


def test_forgets_mocks_when_asked_to_tear_down(
        test_harness: TestHarness, aws_resource_registry: AwsResourceRegistry,
        invocation_handler_repeating_task_scheduler: RepeatingTaskScheduler,
        invocation_post_office: InvocationPostOffice
) -> None:
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: resource_id + 'ARN')
    when_calling(invocation_handler_repeating_task_scheduler.scheduled).always_return(False)
    when_calling(invocation_post_office.maybe_collect_invocation).always_return(
        an_invocation_with(target='OrangeAWSTestHarnessStateMachineARN')
    )

    test_harness.twin_state_machine('Orange')

    verify(invocation_handler_repeating_task_scheduler.schedule).was_called()
    scheduled_task = inspect(invocation_handler_repeating_task_scheduler.schedule).call_args[0][0]

    test_harness.tear_down()

    with pytest.raises(UnknownInvocationTargetException):
        scheduled_task()
