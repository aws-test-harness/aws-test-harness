import logging
import os
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from aws_test_harness_test_support import load_test_configuration
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from tests.support.s3_test_client import S3TestClient


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    return load_test_configuration()


@pytest.fixture(scope="session")
def cfn_stack_name_prefix(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackNamePrefix'] + 'python-library-'


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def aws_profile(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsProfile']


@pytest.fixture(scope="session")
def boto_session(aws_profile: str) -> Session:
    return Session(profile_name=aws_profile)


@pytest.fixture(scope="session")
def system_command_executor(logger: Logger) -> SystemCommandExecutor:
    return SystemCommandExecutor(logger)


@pytest.fixture(scope="session")
def s3_test_client(boto_session: Session) -> S3TestClient:
    return S3TestClient(boto_session)


@pytest.fixture(scope="session")
def infrastructure_directory_path() -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../../infrastructure'))


@pytest.fixture(scope="session")
def test_doubles_template_file_name(infrastructure_directory_path: str) -> str:
    return 'test-doubles.yaml'


@pytest.fixture(scope="session")
def test_doubles_template_path(infrastructure_directory_path: str, test_doubles_template_file_name: str) -> str:
    return os.path.normpath(os.path.join(infrastructure_directory_path, f'templates/{test_doubles_template_file_name}'))
