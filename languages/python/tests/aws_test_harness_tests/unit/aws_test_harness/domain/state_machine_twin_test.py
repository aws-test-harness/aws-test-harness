from aws_test_harness.domain.state_machine_twin import StateMachineTwin
from aws_test_harness_tests.support.builders.invocation_builder import any_invocation, an_invocation_with


def test_reports_how_many_times_state_machine_was_invoked() -> None:
    state_machine_twin = StateMachineTwin()
    assert state_machine_twin.invocation_count == 0

    state_machine_twin.get_result_for(any_invocation())
    assert state_machine_twin.invocation_count == 1

    state_machine_twin.get_result_for(any_invocation())
    assert state_machine_twin.invocation_count == 2


def test_reports_args_for_each_invocation() -> None:
    state_machine_twin = StateMachineTwin()
    state_machine_twin.get_result_for(an_invocation_with(parameters=dict(input=dict(message='message 1'))))
    state_machine_twin.get_result_for(an_invocation_with(parameters=dict(input=dict(message='message 2'))))
    state_machine_twin.get_result_for(an_invocation_with(parameters=dict(input=dict(message='message 3'))))

    invocations = state_machine_twin.invocations

    assert len(invocations) == 3
    assert invocations[0][0]['message'] == 'message 1'
    assert invocations[1][0]['message'] == 'message 2'
    assert invocations[2][0]['message'] == 'message 3'


def test_does_not_share_invocation_history_across_instances() -> None:
    twin_1 = StateMachineTwin()
    twin_1.get_result_for(an_invocation_with(parameters=dict(input=dict(message='message 1'))))

    twin_2 = StateMachineTwin()
    twin_2.get_result_for(an_invocation_with(parameters=dict(input=dict(message='message 2'))))

    assert len(twin_1.invocations) == 1


def test_guards_against_external_mutation_of_invocation_history() -> None:
    state_machine_twin = StateMachineTwin()
    state_machine_twin.get_result_for(an_invocation_with(parameters=dict(input=dict(message='the message'))))
    assert state_machine_twin.invocations[0][0]['message'] == 'the message'

    state_machine_twin.invocations[0][0]['message'] = 'modified message'

    assert state_machine_twin.invocations[0][0]['message'] == 'the message'


def test_generates_invocation_result_using_provided_execution_handler_and_input() -> None:
    state_machine_twin = StateMachineTwin(
        lambda execution_input: dict(receivedMessage=execution_input['message'])
    )
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    result = state_machine_twin.get_result_for(invocation)

    assert result == dict(status='succeeded', context=dict(result=dict(receivedMessage='the message')))


def test_uses_default_invocation_handler_when_none_provided() -> None:
    state_machine_twin = StateMachineTwin()

    result = state_machine_twin.get_result_for(any_invocation())

    assert result == dict(status='succeeded', context=dict(dict(result=dict())))


def test_supports_updating_execution_handler() -> None:
    state_machine_twin = StateMachineTwin(
        lambda execution_input: dict(receivedMessage=execution_input['message'])
    )
    invocation = an_invocation_with(parameters=dict(input=dict(message='the message')))

    state_machine_twin.handle_executions_using(lambda execution_input: dict(
        receivedMessage=execution_input['message'].upper()
    ))

    result = state_machine_twin.get_result_for(invocation)
    assert result == dict(status='succeeded', context=dict(dict(result=dict(receivedMessage='THE MESSAGE'))))
