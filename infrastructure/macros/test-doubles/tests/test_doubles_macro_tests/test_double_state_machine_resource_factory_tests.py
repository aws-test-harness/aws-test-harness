from logging import Logger
from typing import cast

import pytest
from boto3 import Session
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_doubles_macro.test_double_state_machine_resource_factory import TestDoubleStateMachineResourceFactory


@pytest.fixture(scope="module")
def example_state_machine_arn(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> str:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-state-machine-resource-factory', logger,
                                    boto_session)
    resource_descriptions = TestDoubleStateMachineResourceFactory.generate_resources('StateMachineRole')

    stack.ensure_state_is(Resources=dict(
        ExampleStateMachine=resource_descriptions.state_machine,
        StateMachineRole=resource_descriptions.role
    ))

    example_state_machine_resource = stack.get_stack_resource('ExampleStateMachine')
    assert example_state_machine_resource is not None
    assert example_state_machine_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    return example_state_machine_resource['PhysicalResourceId']


@pytest.fixture(scope="module")
def step_functions_client(boto_session: Session) -> SFNClient:
    return cast(SFNClient, boto_session.client('stepfunctions'))


def test_generates_cloudformation_resources_for_executable_state_machine(example_state_machine_arn: str,
                                                                         step_functions_client: SFNClient) -> None:
    result = step_functions_client.start_execution(stateMachineArn=example_state_machine_arn, input='{}')

    assert 'executionArn' in result
