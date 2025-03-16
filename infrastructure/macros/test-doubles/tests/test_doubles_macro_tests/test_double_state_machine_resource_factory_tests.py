import json
from logging import Logger
from typing import cast

import pytest
from boto3 import Session
from mypy_boto3_sqs.client import SQSClient
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_doubles_macro.test_double_state_machine_resource_factory import TestDoubleStateMachineResourceFactory
from infrastructure_test_support.step_functions_utils import execute_state_machine


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-state-machine-resource-factory', logger,
                                    boto_session)
    resource_descriptions = TestDoubleStateMachineResourceFactory.generate_resources(
        'StateMachineRole',
        'EventEchoingFunction'
    )

    stack.ensure_state_is(
        Transform=['AWS::Serverless-2016-10-31'],
        Resources=dict(
            ExampleStateMachine=resource_descriptions.state_machine,
            StateMachineRole=resource_descriptions.role,
            EventEchoingFunction=dict(
                Type='AWS::Serverless::Function',
                Properties=dict(
                    Runtime='python3.13',
                    Handler='index.handler',
                    InlineCode='handler = lambda event, context: dict(receivedEvent=event)'
                )
            )
        ))

    return stack


@pytest.fixture(scope="module")
def example_state_machine_arn(test_stack: TestCloudFormationStack) -> str:
    example_state_machine_resource = test_stack.get_stack_resource('ExampleStateMachine')
    assert example_state_machine_resource is not None
    assert example_state_machine_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    return example_state_machine_resource['PhysicalResourceId']


@pytest.fixture(scope="module")
def step_functions_client(boto_session: Session) -> SFNClient:
    return cast(SFNClient, boto_session.client('stepfunctions'))


@pytest.fixture(scope="module")
def sqs_client(boto_session: Session) -> SQSClient:
    return cast(SQSClient, boto_session.client('sqs'))


def test_generates_cloudformation_resources_for_a_state_machine_that_delegates_invocation_handling_to_lambda_function(
        example_state_machine_arn: str, step_functions_client: SFNClient, sqs_client: SQSClient,
        test_stack: TestCloudFormationStack) -> None:
    execution_description = execute_state_machine(
        example_state_machine_arn,
        step_functions_client,
        execution_input=dict(colour='orange', size='small'),
    )

    execution_output = json.loads(execution_description['output'])
    echoing_function_event = execution_output['receivedEvent']
    assert echoing_function_event['invocationId'] == execution_description['executionArn']
    assert echoing_function_event['executionInput'] == dict(colour='orange', size='small')
