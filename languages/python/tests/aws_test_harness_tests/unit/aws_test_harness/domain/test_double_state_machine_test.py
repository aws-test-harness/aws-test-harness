import pytest

from aws_test_harness.domain.test_double_state_machine import TestDoubleStateMachine
from aws_test_harness_tests.support.builders.invocation_builder import any_invocation, an_invocation_with


def test_reports_how_many_times_state_machine_was_invoked() -> None:
    test_double_state_machine = TestDoubleStateMachine()
    assert test_double_state_machine.call_count == 0

    test_double_state_machine.get_result_for(any_invocation())
    assert test_double_state_machine.call_count == 1

    test_double_state_machine.get_result_for(any_invocation())
    assert test_double_state_machine.call_count == 2


def test_asserts_whether_state_machine_was_called_once_with_specified_input() -> None:
    test_double_state_machine = TestDoubleStateMachine()
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    test_double_state_machine.get_result_for(invocation)

    with pytest.raises(AssertionError, match='expected call not found'):
        test_double_state_machine.assert_called_once_with(dict(message='not the message'))

    test_double_state_machine.assert_called_once_with(dict(message='the message'))


def test_generates_invocation_result_using_provided_execution_handler_and_input() -> None:
    test_double_state_machine = TestDoubleStateMachine(
        lambda execution_input: dict(receivedMessage=execution_input['message'])
    )
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    result = test_double_state_machine.get_result_for(invocation)

    assert result == dict(receivedMessage='the message')


def test_uses_default_invocation_handler_when_none_provided() -> None:
    test_double_state_machine = TestDoubleStateMachine()

    result = test_double_state_machine.get_result_for(any_invocation())

    assert result == dict()
