import json
from unittest.mock import call

import pytest

from step_functions_sandbox_client.a_thrown_exception import an_exception_thrown_with_message
from step_functions_sandbox_client.aws_resource_driver import AWSResourceDriver
from step_functions_sandbox_client.aws_resource_mocking_engine import AWSResourceMockingEngine


@pytest.fixture(scope="function", autouse=True)
def setup_default_mock_behaviour(mocking_engine: AWSResourceMockingEngine):
    mocking_engine.mock_a_lambda_function(
        'InputTransformerFunction',
        lambda event: {'number': event['data']['number']}
    )

    mocking_engine.mock_a_lambda_function(
        'DoublerFunction',
        lambda event: {'number': event['number']}
    )


def test_state_machine_transforms_input(mocking_engine: AWSResourceMockingEngine, resource_driver: AWSResourceDriver):
    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformerFunction')
    input_transformer_function.side_effect = lambda event: {'number': event['data']['number'] + 1}

    doubler_function = mocking_engine.get_mock_lambda_function('DoublerFunction')
    doubler_function.side_effect = lambda event: {'number': event['number'] * 2}

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({'input': {'data': {'number': 1}}})

    assert json.loads(final_state['output']) == {'result': {'number': 4}}

    input_transformer_function.assert_called_with({'data': {'number': 1}})
    doubler_function.assert_called_with({'number': 2})


def test_state_machine_retries_input_transformation_twice(mocking_engine: AWSResourceMockingEngine,
                                                          resource_driver: AWSResourceDriver):
    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformerFunction')
    input_transformer_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({'input': {'data': {'number': 1}}})

    assert json.loads(final_state['output']) == {'result': {'number': 2}}

    input_transformer_function.assert_has_calls([
        call({'data': {'number': 1}}),
        call({'data': {'number': 1}}),
        call({'data': {'number': 1}})
    ])


def test_state_machine_retries_doubling_twice(mocking_engine: AWSResourceMockingEngine,
                                              resource_driver: AWSResourceDriver):
    doubler_function = mocking_engine.get_mock_lambda_function('DoublerFunction')
    doubler_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({'input': {'data': {'number': 1}}})

    assert json.loads(final_state['output']) == {'result': {'number': 2}}

    doubler_function.assert_has_calls([
        call({'number': 1}),
        call({'number': 1}),
        call({'number': 1})
    ])
