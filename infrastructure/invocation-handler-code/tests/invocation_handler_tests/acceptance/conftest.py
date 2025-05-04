import logging
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from aws_test_harness_test_support import load_test_configuration
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    return load_test_configuration()


@pytest.fixture(scope="session")
def aws_profile(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsProfile']


@pytest.fixture(scope="session")
def aws_region(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsRegion']


@pytest.fixture(scope="session")
def cfn_stack_name_prefix(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackNamePrefix'] + 'test-double-invocation-handler-tests-'


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(aws_profile: str, aws_region: str) -> Session:
    return Session(profile_name=aws_profile, region_name=aws_region)


@pytest.fixture(scope="session")
def system_command_executor(boto_session: Session, logger: Logger) -> SystemCommandExecutor:
    return SystemCommandExecutor(logger)
