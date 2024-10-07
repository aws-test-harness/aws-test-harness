import os

import boto3
import pytest
from boto3 import Session

from aws_resource_mocking_engine import AWSResourceMockingEngine
from boto_session_factory import BotoSessionFactory
from cloudformation_stack import CloudFormationStack
from json_file_configuration import JsonFileConfiguration


@pytest.fixture(scope="session")
def configuration():
    return JsonFileConfiguration(os.path.join(os.path.dirname(__file__), '..', 'config.json'))


@pytest.fixture(scope="session")
def developer_boto_session(configuration: JsonFileConfiguration):
    return boto3.session.Session(profile_name=configuration.get_key('awsProfile'))


@pytest.fixture(scope="session")
def cloudformation_stack(configuration: JsonFileConfiguration, developer_boto_session: Session):
    return CloudFormationStack(
        configuration.get_key('sandboxStackName'),
        developer_boto_session
    )


@pytest.fixture(scope="session")
def tester_boto_session(cloudformation_stack: CloudFormationStack, developer_boto_session: Session):
    boto_session_factory = BotoSessionFactory(developer_boto_session)

    return boto_session_factory.create_boto_session_with_assumed_role(
        cloudformation_stack.get_physical_resource_id_for("TesterRole")
    )


@pytest.fixture(scope="session")
def mocking_engine(cloudformation_stack: CloudFormationStack, tester_boto_session: Session):
    return AWSResourceMockingEngine(cloudformation_stack, tester_boto_session)


@pytest.fixture(scope="function", autouse=True)
def reset_mocking_engine(mocking_engine: AWSResourceMockingEngine):
    mocking_engine.reset()
