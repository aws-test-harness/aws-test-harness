import json
import logging
import os
from logging import Logger
from typing import Dict, cast

import pytest
from boto3 import Session

from aws_test_harness_test_support.cloudformation_driver import CloudFormationDriver
from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine import StateMachine
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    configuration_file_path = os.path.join(os.path.dirname(__file__), 'config.json')

    with open(configuration_file_path, 'r') as f:
        return cast(Dict[str, str], json.load(f))


@pytest.fixture(scope="session")
def boto_session(test_configuration: Dict[str, str]) -> Session:
    return Session(profile_name=test_configuration['awsProfile'])


@pytest.fixture(scope="session")
def cloudformation_test_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackName']


@pytest.fixture(scope="session")
def cloudformation_driver(boto_session: Session, logger: Logger) -> CloudFormationDriver:
    return CloudFormationDriver(boto_session.client('cloudformation'), logger)


@pytest.fixture(scope="session")
def test_cloudformation_stack(cloudformation_test_stack_name: str,
                              cloudformation_driver: CloudFormationDriver) -> TestCloudFormationStack:
    return TestCloudFormationStack(cloudformation_test_stack_name, cloudformation_driver)


@pytest.fixture(scope="session")
def state_machine(boto_session: Session, logger: Logger, cloudformation_test_stack_name: str) -> StateMachine:
    resource_registry = ResourceRegistry(boto_session)
    state_machine_arn = resource_registry.get_physical_resource_id('StateMachine', cloudformation_test_stack_name)
    return StateMachine(state_machine_arn, boto_session, logger)


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_definition = dict(
        StartAt='SetResult',
        States=dict(
            SetResult=dict(Type='Pass', Parameters={'result.$': '$.input'}, End=True)
        )
    )
    test_cloudformation_stack.ensure_state_is(
        AWSTemplateFormatVersion='2010-09-09',
        Transform='AWS::Serverless-2016-10-31',
        Resources=dict(
            StateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(Definition=state_machine_definition)
            )
        )
    )


def test_detecting_a_successful_step_function_execution(state_machine: StateMachine,
                                                        cloudformation_test_stack_name: str) -> None:
    execution = state_machine.execute({'input': 'Any input'})

    assert execution.status == 'SUCCEEDED'

    assert execution.output is not None
    assert json.loads(execution.output) == {"result": "Any input"}


def test_detecting_a_failed_step_function_execution(state_machine: StateMachine,
                                                    cloudformation_test_stack_name: str) -> None:
    execution = state_machine.execute({})

    assert execution.status == 'FAILED'

    cause = execution.cause
    assert cause is not None
    assert "JSONPath '$.input' specified for the field 'result.$' could not be found in the input" in cause

    error = execution.error
    assert error == 'States.Runtime'
