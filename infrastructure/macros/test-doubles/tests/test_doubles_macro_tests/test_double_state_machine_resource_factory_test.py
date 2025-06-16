import json
from logging import Logger
from typing import cast

import pytest
from boto3 import Session
from mypy_boto3_sqs.client import SQSClient
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.step_functions_utils import execute_state_machine, \
    assert_describes_successful_execution, assert_describes_failed_execution
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_doubles_macro.test_double_state_machine_resource_factory import TestDoubleStateMachineResourceFactory


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    return TestCloudFormationStack(
        f'{cfn_stack_name_prefix}test-double-state-machine-resource-factory', logger, boto_session
    )


@pytest.fixture(scope="module")
def step_functions_client(boto_session: Session) -> SFNClient:
    return cast(SFNClient, boto_session.client('stepfunctions'))


@pytest.fixture(scope="module")
def sqs_client(boto_session: Session) -> SQSClient:
    return cast(SQSClient, boto_session.client('sqs'))


def test_generates_cloudformation_resources_for_a_state_machine_that_returns_output_as_instructed_by_invocation_handling_lambda_function(
        step_functions_client: SFNClient, sqs_client: SQSClient,
        test_stack: TestCloudFormationStack) -> None:
    resource_descriptions = TestDoubleStateMachineResourceFactory.generate_resources(
        'StateMachineRole',
        'EventEchoingFunction'
    )

    test_stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31'],
        Resources=dict(
            ExampleStateMachine=resource_descriptions.state_machine,
            StateMachineRole=resource_descriptions.role,
            EventEchoingFunction=dict(
                Type='AWS::Serverless::Function',
                Properties=dict(
                    Runtime='python3.13',
                    Handler='index.handler',
                    InlineCode="handler = lambda event, context: dict(invocationResult=dict(status='succeeded', context=dict(result=event)))"
                )
            )
        ))

    example_state_machine_arn = get_example_state_machine_arn(test_stack)

    execution_description = execute_state_machine(
        example_state_machine_arn,
        step_functions_client,
        execution_input=dict(colour='orange', size='small'),
    )
    assert_describes_successful_execution(execution_description)

    echoing_function_event = json.loads(execution_description['output'])
    assert 'invocationId' in echoing_function_event
    assert echoing_function_event['invocationId'] == execution_description['executionArn']

    assert 'invocationTarget' in echoing_function_event
    assert echoing_function_event['invocationTarget'] == example_state_machine_arn

    assert 'invocationParameters' in echoing_function_event
    assert echoing_function_event['invocationParameters'] == dict(input=dict(colour='orange', size='small'))


def test_generates_cloudformation_resources_for_a_state_machine_that_fails_if_instructed_by_invocation_handling_lambda_function(
        step_functions_client: SFNClient, sqs_client: SQSClient,
        test_stack: TestCloudFormationStack) -> None:
    resource_descriptions = TestDoubleStateMachineResourceFactory.generate_resources(
        'StateMachineRole',
        'EventEchoingFunction'
    )

    test_stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31'],
        Resources=dict(
            ExampleStateMachine=resource_descriptions.state_machine,
            StateMachineRole=resource_descriptions.role,
            EventEchoingFunction=dict(
                Type='AWS::Serverless::Function',
                Properties=dict(
                    Runtime='python3.13',
                    Handler='index.handler',
                    InlineCode="handler = lambda event, context: dict(invocationResult=dict(status='failed', context=dict(error='TheExpectedError', cause='the expected cause')))"
                )
            )
        ))

    example_state_machine_arn = get_example_state_machine_arn(test_stack)

    execution_description = execute_state_machine(
        example_state_machine_arn,
        step_functions_client,
        execution_input=dict(colour='orange', size='small'),
    )
    assert_describes_failed_execution(execution_description, 'the expected cause', 'TheExpectedError')


def get_example_state_machine_arn(test_stack: TestCloudFormationStack) -> str:
    example_state_machine_resource = test_stack.get_stack_resource('ExampleStateMachine')
    assert example_state_machine_resource is not None
    assert example_state_machine_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    return example_state_machine_resource['PhysicalResourceId']
