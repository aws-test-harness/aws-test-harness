import json
import logging
import os
from logging import Logger
from typing import Dict, cast

import pytest
from boto3 import Session

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    configuration_file_path = os.path.join(os.path.dirname(__file__), 'config.json')

    with open(configuration_file_path, 'r') as f:
        return cast(Dict[str, str], json.load(f))


@pytest.fixture(scope="session")
def aws_profile(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsProfile']


@pytest.fixture(scope="session")
def cfn_test_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackName']


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def test_cloudformation_stack(cfn_test_stack_name: str, aws_profile: str, logger: Logger) -> TestCloudFormationStack:
    boto_session = Session(profile_name=aws_profile)
    return TestCloudFormationStack(cfn_test_stack_name, logger, boto_session)
