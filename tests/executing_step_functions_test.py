import json
import logging
import os
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from support.cloudformation_driver import CloudFormationDriver
from aws_test_harness.cloudformation_resource_registry import CloudFormationResourceRegistry
from aws_test_harness.state_machine_driver import StateMachineDriver


@pytest.fixture(scope="session")
def logger():
    return logging.getLogger()


@pytest.fixture(scope="session")
def test_configuration():
    configuration_file_path = os.path.join(os.path.dirname(__file__), 'config.json')

    with open(configuration_file_path, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def boto_session(test_configuration: Dict[str, str]):
    return Session(profile_name=test_configuration['awsProfile'])


@pytest.fixture(scope="session")
def cloudformation_stack_name(test_configuration: Dict[str, str]):
    return test_configuration['cfnStackName']


@pytest.fixture(scope="session")
def cloudformation_driver(boto_session: Session, logger: Logger):
    return CloudFormationDriver(boto_session.client('cloudformation'), logger)


@pytest.fixture(scope="session")
def state_machine_driver(cloudformation_driver: CloudFormationDriver, boto_session: Session, logger: Logger):
    cloudformation_resource_registry = CloudFormationResourceRegistry(boto_session)
    return StateMachineDriver(cloudformation_resource_registry, boto_session, logger)


@pytest.fixture(scope="session", autouse=True)
def before_all(cloudformation_driver: CloudFormationDriver, cloudformation_stack_name: str):
    state_machine_definition = dict(
        StartAt='SetResult',
        States=dict(
            SetResult=dict(Type='Pass', Parameters={'result.$': '$.input'}, End=True)
        )
    )

    cloudformation_driver.ensure_stack_is_up_to_date(
        cloudformation_stack_name,
        dict(
            AWSTemplateFormatVersion='2010-09-09',
            Transform='AWS::Serverless-2016-10-31',
            Resources=dict(
                StateMachine=dict(
                    Type='AWS::Serverless::StateMachine',
                    Properties=dict(Definition=state_machine_definition)
                )
            )
        )
    )


def test_detecting_a_successful_step_function_execution(state_machine_driver: StateMachineDriver,
                                                        cloudformation_stack_name: str):
    execution_result = state_machine_driver.start_execution({'input': 'Any input'}, 'StateMachine',
                                                            cloudformation_stack_name)

    assert execution_result.status == 'SUCCEEDED'

    assert execution_result.output is not None
    assert json.loads(execution_result.output) == {"result": "Any input"}


def test_detecting_a_failed_step_function_execution(state_machine_driver: StateMachineDriver,
                                                    cloudformation_stack_name: str):
    execution_result = state_machine_driver.start_execution({}, 'StateMachine',
                                                            cloudformation_stack_name)

    assert execution_result.status == 'FAILED'

    cause = execution_result.cause
    assert cause is not None
    assert "JSONPath '$.input' specified for the field 'result.$' could not be found in the input" in cause

    error = execution_result.error
    assert error == 'States.Runtime'
