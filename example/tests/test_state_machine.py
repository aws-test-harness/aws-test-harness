import json
from unittest.mock import call
from uuid import uuid4

import pytest

from step_functions_sandbox_client.a_thrown_exception import an_exception_thrown_with_message
from step_functions_sandbox_client.aws_resource_driver import AWSResourceDriver
from step_functions_sandbox_client.aws_resource_mocking_engine import AWSResourceMockingEngine
from step_functions_sandbox_client.aws_test_double_driver import AWSTestDoubleDriver


@pytest.fixture(scope="function", autouse=True)
def setup_default_mock_behaviour(mocking_engine: AWSResourceMockingEngine,
                                 test_double_driver: AWSTestDoubleDriver):
    mocking_engine.mock_a_lambda_function(
        'InputTransformer',
        lambda event: {'number': event['data']['number']}
    )

    mocking_engine.mock_a_lambda_function(
        'Doubler',
        lambda event: {'number': event['number'], 'objectKey': 'any-object-key'}
    )

    first_bucket = test_double_driver.get_s3_bucket('First')
    first_bucket.put_object('default-message', 'default message')


def test_state_machine_transforms_input(mocking_engine: AWSResourceMockingEngine, resource_driver: AWSResourceDriver,
                                        test_double_driver: AWSTestDoubleDriver):
    first_bucket = test_double_driver.get_s3_bucket('First')
    first_bucket_key = f'data/message-{uuid4()}'
    first_bucket.put_object(first_bucket_key, 'This is the retrieved message')

    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformer')
    input_transformer_function.side_effect = lambda event: {'number': event['data']['number'] + 1}

    doubler_function = mocking_engine.get_mock_lambda_function('Doubler')

    second_bucket = test_double_driver.get_s3_bucket('Second')

    def doubler_function_handler(event):
        number = event["number"]
        object_key = str(uuid4())
        second_bucket.put_object(object_key, f'Number passed to doubler function: {number}')
        return {'number': number * 2, 'objectKey': object_key}

    doubler_function.side_effect = doubler_function_handler

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': first_bucket_key
        }
    })

    final_state_output_data = json.loads(final_state['output'])

    assert 'double' in final_state_output_data
    assert 'result' in final_state_output_data['double']
    assert 'number' in final_state_output_data['double']['result']
    assert final_state_output_data['double']['result']['number'] == 4

    assert 'getObject' in final_state_output_data
    assert 'result' in final_state_output_data['getObject']
    assert final_state_output_data['getObject']['result'] == 'This is the retrieved message'

    assert 'objectKey' in final_state_output_data['double']['result']
    object_key_from_result = final_state_output_data['double']['result']['objectKey']

    object_content = second_bucket.get_object(object_key_from_result)
    assert object_content == 'Number passed to doubler function: 2'

    input_transformer_function.assert_called_with({'data': {'number': 1}})
    doubler_function.assert_called_with({'number': 2})


def test_state_machine_retries_input_transformation_twice(mocking_engine: AWSResourceMockingEngine,
                                                          resource_driver: AWSResourceDriver):
    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformer')
    input_transformer_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message'
        }
    })

    assert json.loads(final_state['output'])['double']['result']['number'] == 2

    input_transformer_function.assert_has_calls([
        call({'data': {'number': 1}}),
        call({'data': {'number': 1}}),
        call({'data': {'number': 1}})
    ])


def test_state_machine_retries_doubling_twice(mocking_engine: AWSResourceMockingEngine,
                                              resource_driver: AWSResourceDriver):
    doubler_function = mocking_engine.get_mock_lambda_function('Doubler')
    doubler_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    final_state = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message'
        }
    })

    assert json.loads(final_state['output'])['double']['result']['number'] == 2

    doubler_function.assert_has_calls([
        call({'number': 1}),
        call({'number': 1}),
        call({'number': 1})
    ])
