import pytest

from aws_test_harness.domain.state_machine_twin import StateMachineTwin
from aws_test_harness_tests.support.builders.invocation_builder import any_invocation, an_invocation_with


def test_reports_how_many_times_state_machine_was_invoked() -> None:
    state_machine_twin = StateMachineTwin()
    assert state_machine_twin.call_count == 0

    state_machine_twin.get_result_for(any_invocation())
    assert state_machine_twin.call_count == 1

    state_machine_twin.get_result_for(any_invocation())
    assert state_machine_twin.call_count == 2


def test_asserts_whether_state_machine_was_called_once_with_specified_input() -> None:
    state_machine_twin = StateMachineTwin()
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    state_machine_twin.get_result_for(invocation)

    with pytest.raises(AssertionError, match='expected call not found'):
        state_machine_twin.assert_called_once_with(dict(message='not the message'))

    state_machine_twin.assert_called_once_with(dict(message='the message'))


def test_generates_invocation_result_using_provided_execution_handler_and_input() -> None:
    state_machine_twin = StateMachineTwin(
        lambda execution_input: dict(receivedMessage=execution_input['message'])
    )
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    result = state_machine_twin.get_result_for(invocation)

    assert result == dict(receivedMessage='the message')


def test_uses_default_invocation_handler_when_none_provided() -> None:
    state_machine_twin = StateMachineTwin()

    result = state_machine_twin.get_result_for(any_invocation())

    assert result == dict()
