import pytest

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation_target_twin_service import InvocationTargetTwinService
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException
from aws_test_harness_test_support.mocking import mock_class, when_calling
from aws_test_harness_tests.support.builders.invocation_builder import an_invocation_with


def test_creates_digital_twin_to_control_test_harness_state_machine() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: f'{resource_id}ARN')
    twin_service = InvocationTargetTwinService(aws_resource_registry)

    twin_service.create_twin_for_state_machine(
        'Orange',
        lambda execution_input: dict(output=execution_input['message'])
    )

    the_input = dict(message='the input')
    invocation = an_invocation_with(target='OrangeAWSTestHarnessStateMachineARN', parameters=dict(input=the_input))
    result = twin_service.generate_result_for_invocation(invocation)
    assert result == dict(status='succeeded', context=dict(result=dict(output='the input')))


def test_associates_each_digital_twin_with_specific_invocation_target() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: f'{resource_id}ARN')
    twin_service = InvocationTargetTwinService(aws_resource_registry)

    twin_service.create_twin_for_state_machine('Orange', lambda _: dict(output='orange output'))
    twin_service.create_twin_for_state_machine('Blue', lambda _: dict(output='blue output'))
    twin_service.create_twin_for_state_machine('Yellow', lambda _: dict(output='yellow output'))

    invocation = an_invocation_with(target='BlueAWSTestHarnessStateMachineARN')
    result = twin_service.generate_result_for_invocation(invocation)
    assert result == dict(status='succeeded', context=dict(result=dict(output='blue output')))


def test_raises_exception_when_asked_to_generate_result_for_unknown_invocation_target() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: f'{resource_id}ARN')
    twin_service = InvocationTargetTwinService(aws_resource_registry)
    twin_service.create_twin_for_state_machine('Orange', lambda _: dict(output='orange output'))
    invocation = an_invocation_with(target='BlueAWSTestHarnessStateMachineARN')

    with pytest.raises(UnknownInvocationTargetException, match='BlueAWSTestHarnessStateMachineARN'):
        twin_service.generate_result_for_invocation(invocation)


def test_forgets_invocation_targets_when_reset() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(lambda resource_id: f'{resource_id}ARN')
    twin_service = InvocationTargetTwinService(aws_resource_registry)

    twin_service.create_twin_for_state_machine('Orange', lambda _: dict(output='orange output'))
    invocation = an_invocation_with(target='OrangeAWSTestHarnessStateMachineARN')
    twin_service.generate_result_for_invocation(invocation)

    twin_service.reset()

    with pytest.raises(UnknownInvocationTargetException, match='OrangeAWSTestHarnessStateMachineARN'):
        twin_service.generate_result_for_invocation(invocation)
