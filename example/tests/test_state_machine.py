import pytest
from datetime import datetime, timedelta
from unittest.mock import call
from uuid import uuid4

from aws_test_harness.a_state_machine_execution_failure import a_state_machine_execution_failure
from aws_test_harness.a_thrown_exception import an_exception_thrown_with_message
from aws_test_harness.exit_code import ExitCode
from aws_test_harness.aws_resource_driver import AWSResourceDriver
from aws_test_harness.aws_resource_mocking_engine import AWSResourceMockingEngine
from aws_test_harness.aws_test_double_driver import AWSTestDoubleDriver


@pytest.fixture(scope="session", autouse=True)
def reset_database(test_double_driver: AWSTestDoubleDriver):
    first_table = test_double_driver.get_dynamodb_table('First')
    first_table.empty()

    second_table = test_double_driver.get_dynamodb_table('Second')
    second_table.empty()


@pytest.fixture(scope="function", autouse=True)
def setup_default_mock_behaviour(mocking_engine: AWSResourceMockingEngine,
                                 test_double_driver: AWSTestDoubleDriver):
    mocking_engine.mock_an_ecs_task(
        'DataProcessor',
        lambda command_args: ExitCode(0)
    )

    mocking_engine.mock_a_lambda_function(
        'InputTransformer',
        lambda event: {'number': event['data']['number']}
    )

    mocking_engine.mock_a_lambda_function(
        'Doubler',
        lambda event: {'number': event['number'], 'objectKey': 'any-object-key'}
    )

    mocking_engine.mock_a_state_machine(
        'Multiplier',
        lambda execution_input: {'number': execution_input['number'] * execution_input['factor']}
    )

    first_bucket = test_double_driver.get_s3_bucket('First')
    first_bucket.put_object('default-message', 'default message')


def test_state_machine_transforms_input(mocking_engine: AWSResourceMockingEngine, resource_driver: AWSResourceDriver,
                                        test_double_driver: AWSTestDoubleDriver):
    data_processor_ecs_task = mocking_engine.get_mock_ecs_task('DataProcessor')

    first_bucket_key = f'data/message-{uuid4()}'
    first_bucket = test_double_driver.get_s3_bucket('First')

    def data_processor_ecs_task_handler(command_args):
        bucket_key = command_args[0]
        content = command_args[1]
        first_bucket.put_object(bucket_key, content)
        return ExitCode(0)

    data_processor_ecs_task.side_effect = data_processor_ecs_task_handler

    first_table = test_double_driver.get_dynamodb_table('First')
    first_table_item_key = str(uuid4())
    first_table.put_item({
        'PK': first_table_item_key,
        'SK': '1',
        'TTL': int((datetime.now() + timedelta(hours=1)).timestamp()),
        'message': 'This is the message retrieved from DynamoDB',
    })

    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformer')
    input_transformer_function.side_effect = lambda event: {'number': event['data']['number'] + 1}

    doubler_function = mocking_engine.get_mock_lambda_function('Doubler')

    second_bucket = test_double_driver.get_s3_bucket('Second')
    second_table = test_double_driver.get_dynamodb_table('Second')

    second_bucket_key = None

    def doubler_function_handler(event):
        nonlocal second_bucket_key

        number = event["number"]
        second_bucket_key = str(uuid4())
        second_bucket.put_object(second_bucket_key, f'Number passed to doubler function: {number}')
        record_key = str(uuid4())
        second_table.put_item({
            'ID': record_key,
            'TTL': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'message': f'Number passed to doubler function: {number}',
        })

        return {'number': number * 2, 'objectKey': second_bucket_key, 'recordKey': record_key}

    doubler_function.side_effect = doubler_function_handler

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    execution = state_machine.start_execution({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': first_bucket_key,
            'firstTableItemKey': first_table_item_key,
            'firstObjectContent': 'Content provided for first S3 object'
        }
    })

    assert execution.name.startswith('test-')

    execution.wait_for_completion(timeout_seconds=90)
    execution.assert_succeeded()

    final_state_output_data = execution.output_json

    multiplier_state_machine = mocking_engine.get_mock_state_machine('Multiplier')
    multiplier_state_machine.assert_called_once()
    multiplier_state_machine_input = multiplier_state_machine.call_args[0][0]
    assert multiplier_state_machine_input['number'] == 4
    assert multiplier_state_machine_input['factor'] == 3

    assert 'multiply' in final_state_output_data
    assert 'result' in final_state_output_data['multiply']
    assert 'number' in final_state_output_data['multiply']['result']
    assert final_state_output_data['multiply']['result']['number'] == 12

    assert 'double' in final_state_output_data
    assert 'result' in final_state_output_data['double']
    assert 'number' in final_state_output_data['double']['result']
    assert final_state_output_data['double']['result']['number'] == 4

    assert 'getObject' in final_state_output_data
    assert 'result' in final_state_output_data['getObject']
    assert final_state_output_data['getObject']['result'] == 'Content provided for first S3 object'
    assert final_state_output_data['getItem']['Item']['message']['S'] == 'This is the message retrieved from DynamoDB'

    assert 'objectKey' in final_state_output_data['double']['result']
    object_key_from_result = final_state_output_data['double']['result']['objectKey']
    object_content = second_bucket.get_object(object_key_from_result)
    assert object_content == 'Number passed to doubler function: 2'

    assert 'recordKey' in final_state_output_data['double']['result']
    record_key_from_result = final_state_output_data['double']['result']['recordKey']
    item = second_table.get_item(dict(ID=record_key_from_result))
    assert item['message'] == 'Number passed to doubler function: 2'

    data_processor_ecs_task.assert_called_once()
    input_transformer_function.assert_called_with({'data': {'number': 1}})
    doubler_function.assert_called_with({'number': 2})

    assert first_bucket_key in first_bucket.list_objects(prefix='data/')
    assert first_bucket.list_objects(prefix='data2/') == []
    assert second_bucket_key in second_bucket.list_objects()


def test_state_machine_retries_input_transformation_once(mocking_engine: AWSResourceMockingEngine,
                                                         resource_driver: AWSResourceDriver):
    input_transformer_function = mocking_engine.get_mock_lambda_function('InputTransformer')
    input_transformer_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    execution = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message',
            'firstTableItemKey': 'any key',
            'skipECSTask': True
        }
    })

    execution.assert_succeeded()
    assert execution.output_json['double']['result']['number'] == 2

    input_transformer_function.assert_has_calls([
        call({'data': {'number': 1}}),
        call({'data': {'number': 1}})
    ])


def test_state_machine_retries_doubling_once(mocking_engine: AWSResourceMockingEngine,
                                             resource_driver: AWSResourceDriver):
    doubler_function = mocking_engine.get_mock_lambda_function('Doubler')
    doubler_function.side_effect = [
        an_exception_thrown_with_message("the error message"),
        {'number': 2},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    execution = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message',
            'firstTableItemKey': 'any key',
            'skipECSTask': True
        }
    })

    execution.assert_succeeded()
    assert execution.output_json['double']['result']['number'] == 2

    doubler_function.assert_has_calls([
        call({'number': 1}),
        call({'number': 1})
    ])


def test_state_machine_retries_multiplying_once(mocking_engine: AWSResourceMockingEngine,
                                                resource_driver: AWSResourceDriver):
    multiplier_state_machine = mocking_engine.get_mock_state_machine('Multiplier')
    multiplier_state_machine.side_effect = [
        a_state_machine_execution_failure(error="TheErrorCode", cause="the failure cause"),
        {'number': 6},
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    execution = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message',
            'firstTableItemKey': 'any key',
            'skipECSTask': True
        }
    })

    execution.assert_succeeded()
    assert execution.output_json['multiply']['result']['number'] == 6
    assert multiplier_state_machine.call_count == 2


def test_state_machine_retries_ecs_task_once(mocking_engine: AWSResourceMockingEngine,
                                             resource_driver: AWSResourceDriver):
    ecs_task = mocking_engine.get_mock_ecs_task('DataProcessor')
    ecs_task.side_effect = [
        ExitCode(1),
        ExitCode(0),
    ]

    state_machine = resource_driver.get_state_machine("ExampleStateMachine::StateMachine")

    execution = state_machine.execute({
        'input': {
            'data': {'number': 1},
            'firstBucketKey': 'default-message',
            'firstTableItemKey': 'any key'
        }
    }, timeout_seconds=240)

    execution.assert_succeeded()
    assert ecs_task.call_count == 2
