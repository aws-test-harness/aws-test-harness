import json

import pytest

from aws_resource_mocking_engine import AWSResourceMockingEngine
from aws_resource_driver import AWSResourceDriver


@pytest.fixture(scope="function", autouse=True)
def run_mocking_engine(mocking_engine: AWSResourceMockingEngine):
    mocking_engine.reset()
    yield
    mocking_engine.stop_listening()


def test_state_machine(mocking_engine: AWSResourceMockingEngine, resource_driver: AWSResourceDriver):
    input_transformer_function = mocking_engine.mock_a_lambda_function(
        'InputTransformerFunction',
        lambda event: {'number': event['data']['number'] + 1}
    )

    doubler_function = mocking_engine.mock_a_lambda_function(
        'DoublerFunction',
        lambda event: {'number': event['number'] * 2}
    )

    state_machine = resource_driver.get_stack_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({'input': {'data': {'number': 1}}})

    assert json.loads(final_state['output']) == {'result': {'number': 4}}

    # TODO: Tolerate eventual consistency
    input_transformer_function.assert_called_with({'data': {'number': 1}})
    doubler_function.assert_called_with({'number': 2})
