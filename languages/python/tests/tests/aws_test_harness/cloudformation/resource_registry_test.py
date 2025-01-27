import logging
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness_test_support.cloudformation_driver import CloudFormationDriver


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(test_configuration: Dict[str, str]) -> Session:
    return Session(profile_name=test_configuration['awsProfile'])


@pytest.fixture(scope="session")
def cloudformation_test_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackName']


@pytest.fixture(scope="session")
def cloudformation_driver(boto_session: Session, logger: Logger) -> CloudFormationDriver:
    return CloudFormationDriver(boto_session.client('cloudformation'), logger)


@pytest.fixture(scope="session", autouse=True)
def before_all(cloudformation_driver: CloudFormationDriver, cloudformation_test_stack_name: str) -> None:
    state_machine_definition = dict(
        StartAt='SetResult',
        States=dict(
            SetResult=dict(Type='Pass', End=True)
        )
    )

    cloudformation_driver.ensure_stack_is_up_to_date(
        cloudformation_test_stack_name,
        dict(
            AWSTemplateFormatVersion='2010-09-09',
            Transform='AWS::Serverless-2016-10-31',
            Resources=dict(
                FirstStateMachine=dict(
                    Type='AWS::Serverless::StateMachine',
                    Properties=dict(Definition=state_machine_definition)
                ),
                SecondStateMachine=dict(
                    Type='AWS::Serverless::StateMachine',
                    Properties=dict(Definition=state_machine_definition)
                )
            ),
            Outputs=dict(
                FirstStateMachineArn=dict(
                    Value=dict(Ref='FirstStateMachine')
                ),
                SecondStateMachineArn=dict(
                    Value=dict(Ref='SecondStateMachine')
                )
            )
        )
    )


def test_provides_physical_id_for_resource_specified_by_logical_id(boto_session: Session,
                                                                   cloudformation_test_stack_name: str,
                                                                   cloudformation_driver: CloudFormationDriver) -> None:
    first_state_machine_arn = cloudformation_driver.get_stack_output_value(cloudformation_test_stack_name,
                                                                           'FirstStateMachineArn')

    resource_registry = ResourceRegistry(boto_session)

    physical_id = resource_registry.get_physical_resource_id('FirstStateMachine', cloudformation_test_stack_name)

    assert physical_id == first_state_machine_arn
