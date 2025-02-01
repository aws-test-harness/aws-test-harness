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
def aws_region(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsRegion']


@pytest.fixture(scope="session")
def test_cfn_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['testCfnStackName']


@pytest.fixture(scope="session")
def test_templates_cfn_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['testTemplatesCfnStackName']


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(aws_profile: str, aws_region: str) -> Session:
    return Session(profile_name=aws_profile, region_name=aws_region)


@pytest.fixture(scope="session")
def test_cloudformation_stack(test_cfn_stack_name: str, boto_session: Session,
                              logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(test_cfn_stack_name, logger, boto_session)


@pytest.fixture(scope="session")
def test_templates_cloudformation_stack(test_templates_cfn_stack_name: str, boto_session: Session,
                                        logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(test_templates_cfn_stack_name, logger, boto_session)
