import json
import pytest
from datetime import datetime, timedelta
from typing import cast
from unittest.mock import ANY
from uuid import uuid4

from aws_test_harness.a_state_machine_execution_failure import a_state_machine_execution_failure
from aws_test_harness.a_thrown_exception import an_exception_thrown_with_message
from aws_test_harness.aws_resource_driver import AWSResourceDriver
from aws_test_harness.aws_resource_mocking_engine import AWSResourceMockingEngine
from aws_test_harness.aws_test_double_driver import AWSTestDoubleDriver
from aws_test_harness.exit_code import ExitCode
from aws_test_harness.state_machine import StateMachine
from aws_test_harness.task_context import TaskContext


@pytest.fixture(scope="function")
def state_machine(resource_driver: AWSResourceDriver):
    return resource_driver.get_state_machine("ExampleStateMachine::StateMachine")


def test_lambda_function_test_double(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    test_double = mocking_engine.mock_a_lambda_function(
        "First",
        lambda event: {"value": event["value"] * 2}
    )

    execution = state_machine.execute({
        "input": {
            "integrationType": "LAMBDA_INVOKE",
            "value": 10
        }
    })

    execution.assert_succeeded()
    assert execution.output_json["lambdaFunctionInvoke"]["result"]["value"] == 20
    test_double.assert_called_once_with({"value": 10})


def test_instructing_lambda_function_test_double_to_fail(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    mocking_engine.mock_a_lambda_function(
        'First',
        lambda _: an_exception_thrown_with_message("the error message")
    )

    execution = state_machine.execute({
        "input": {
            "integrationType": "LAMBDA_INVOKE",
            "value": 10
        }
    })

    assert execution.failed
    assert execution.failure_error == "Exception"
    failure_cause_data = json.loads(execution.failure_cause)
    assert failure_cause_data['errorMessage'] == "the error message"


def test_state_machine_test_double_with_start_execution_sync_integration(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    test_double = mocking_engine.mock_a_state_machine(
        "First",
        lambda execution_input: dict(result=execution_input["value"] * 3)
    )

    execution = state_machine.execute({
        "input": {
            "integrationType": "STATES_START_EXECUTION_SYNC",
            "value": 4
        }
    })

    execution.assert_succeeded()
    assert execution.output_json["statesStartExecutionSync"]["result"] == 12
    test_double.assert_called_once_with({
        "value": 4,
        "AWS_STEP_FUNCTIONS_STARTED_BY_EXECUTION_ID": ANY
    })


def test_instructing_state_machine_test_double_to_fail(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    mocking_engine.mock_a_state_machine(
        'First',
        lambda _: a_state_machine_execution_failure(error="TheErrorCode", cause="the failure cause")
    )

    execution = state_machine.execute({
        "input": {
            "integrationType": "STATES_START_EXECUTION_SYNC",
            "value": 0
        }
    })

    assert execution.failed
    assert execution.failure_error == "States.TaskFailed"

    failure_cause_data = json.loads(execution.failure_cause)
    assert failure_cause_data['Error'] == "TheErrorCode"
    assert failure_cause_data['Cause'] == "the failure cause"


def test_dynamodb_test_double(
        mocking_engine: AWSResourceMockingEngine,
        test_double_driver: AWSTestDoubleDriver,
        state_machine: StateMachine
):
    first_test_double = test_double_driver.get_dynamodb_table("First")
    first_item_key = str(uuid4())
    first_item_sort_key = str(uuid4())
    dynamodb_record_ttl = int((datetime.now() + timedelta(hours=1)).timestamp())

    first_test_double.put_item(
        {
            "PK": first_item_key,
            "SK": first_item_sort_key,
            "message": "Hello World!",
            "TTL": dynamodb_record_ttl,
        }
    )

    second_item_key = str(uuid4())

    execution = state_machine.execute(
        {
            "input": {
                "integrationType": "DYNAMODB",
                "firstKey": first_item_key,
                "sortKey": first_item_sort_key,
                "secondKey": second_item_key,
                "textToAppend": " - Processed",
                "dynamodbRecordTTL": dynamodb_record_ttl,
            }
        }
    )

    execution.assert_succeeded()

    second_test_double = test_double_driver.get_dynamodb_table("Second")
    second_item = second_test_double.get_item({"ID": second_item_key})
    assert second_item["message"] == "Hello World! - Processed"


def test_s3_test_double(
        mocking_engine: AWSResourceMockingEngine,
        test_double_driver: AWSTestDoubleDriver,
        state_machine: StateMachine
):
    first_test_double = test_double_driver.get_s3_bucket("First")
    first_object_key = f"input/{uuid4()}.txt"
    first_test_double.put_object(first_object_key, "Hello S3 World!")

    second_object_key = f"output/{uuid4()}.txt"

    execution = state_machine.execute(
        {
            "input": {
                "integrationType": "S3",
                "firstKey": first_object_key,
                "secondKey": second_object_key,
                "textToAppend": " - Processed",
            }
        }
    )

    execution.assert_succeeded()

    second_test_double = test_double_driver.get_s3_bucket("Second")
    output_content = second_test_double.get_object(second_object_key)
    assert output_content == '"Hello S3 World! - Processed"'


def test_ecs_task_test_double_with_run_task_sync_integration(
        mocking_engine: AWSResourceMockingEngine,
        test_double_driver: AWSTestDoubleDriver,
        state_machine: StateMachine
):
    bucket = test_double_driver.get_s3_bucket("First")

    def ecs_task_handler(task_context):
        s3_object_key = task_context.command_args[0]
        greeting_template = task_context.command_args[1]

        bucket.put_object(
            key=s3_object_key,
            content=greeting_template.format(
                first_name=task_context.env_vars["FIRST_NAME"],
                last_name=task_context.env_vars["LAST_NAME"],
            )
        )

        return ExitCode(0)

    test_double = mocking_engine.mock_an_ecs_task("First", ecs_task_handler)

    output_key = f"{uuid4()}.txt"

    execution = state_machine.execute(
        {
            "input": {
                "integrationType": "ECS_RUN_TASK_SYNC",
                "outputKey": output_key,
                "greetingTemplate": "Hello {first_name} {last_name}!",
                "firstName": "ECS",
                "lastName": "Developer",
            }
        },
        timeout_seconds=60
    )

    execution.assert_succeeded()
    assert execution.output_json["ecsRunTaskSync"]["Containers"][0]["ExitCode"] == 0

    test_double.assert_called_once_with(TaskContext(
        command_args=[output_key, "Hello {first_name} {last_name}!"],
        env_vars=ANY
    ))

    ecs_task_arg = cast(TaskContext, test_double.call_args.args[0])
    assert ecs_task_arg.env_vars['FIRST_NAME'] == "ECS"
    assert ecs_task_arg.env_vars['LAST_NAME'] == "Developer"
    assert bucket.get_object(output_key) == "Hello ECS Developer!"


def test_instructing_ecs_task_test_double_to_fail(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    mocking_engine.mock_an_ecs_task('First', lambda _: ExitCode(1))

    execution = state_machine.execute(
        {
            "input": {
                "integrationType": "ECS_RUN_TASK_SYNC",
                "outputKey": 'any-output-key.txt',
                "greetingTemplate": "any greeting template",
                "firstName": "any first name",
                "lastName": "any last name",
            }
        },
        timeout_seconds=60
    )

    assert execution.failed
    assert execution.failure_error == "States.TaskFailed"
    failure_cause_data = json.loads(execution.failure_cause)
    assert failure_cause_data["Containers"][0]["ExitCode"] == 1


def test_ecs_task_callback_pattern_returns_processed_greeting(
        mocking_engine: AWSResourceMockingEngine,
        state_machine: StateMachine
):
    def ecs_callback_handler(task_context):
        task_token = task_context.env_vars.get("AWS_STEP_FUNCTIONS_TASK_TOKEN")
        greeting_template = task_context.command_args[1]

        rendered_greeting = greeting_template.format(
            first_name=task_context.env_vars["FIRST_NAME"],
            last_name=task_context.env_vars["LAST_NAME"],
        )

        state_machine.send_task_success(task_token, {"greeting": rendered_greeting})
        return ExitCode(0)

    mocking_engine.mock_an_ecs_task("First", ecs_callback_handler)

    execution = state_machine.execute(
        {
            "input": {
                "integrationType": "ECS_RUN_TASK_CALLBACK",
                "outputKey": "test-output.txt",
                "greetingTemplate": "Hello {first_name} {last_name}!",
                "firstName": "Test",
                "lastName": "User",
            }
        },
        timeout_seconds=60
    )

    execution.assert_succeeded()
    assert execution.output_json["ecsRunTaskCallback"]["greeting"] == "Hello Test User!"
