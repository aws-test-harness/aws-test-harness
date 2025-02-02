import json
import logging
import os
from logging import Logger
from typing import Dict, cast

import pytest
from boto3 import Session


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    configuration_file_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    with open(configuration_file_path, 'r') as f:
        return cast(Dict[str, str], json.load(f))


@pytest.fixture(scope="session")
def cfn_stack_name_prefix(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackNamePrefix']


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(test_configuration: Dict[str, str]) -> Session:
    return Session(profile_name=test_configuration['awsProfile'])


@pytest.fixture(scope="session")
def test_doubles_template_path() -> str:
    return os.path.join(os.path.dirname(__file__), '../../../../infrastructure/test-doubles.yaml')
