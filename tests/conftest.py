import logging
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from aws_test_harness_test_support import load_test_configuration
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack


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
    return test_configuration['cfnStackNamePrefix']


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(aws_profile: str, aws_region: str) -> Session:
    return Session(profile_name=aws_profile, region_name=aws_region)


@pytest.fixture(scope="session")
def system_command_executor(boto_session: Session, logger: Logger) -> SystemCommandExecutor:
    return SystemCommandExecutor(logger)


@pytest.fixture(scope="session")
def test_cloudformation_stack(cfn_stack_name_prefix: str, boto_session: Session,
                              logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(cfn_stack_name_prefix + 'acceptance-test', logger, boto_session)


@pytest.fixture(scope="session")
def s3_deployment_assets_bucket_name(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> str:
    stack = TestS3BucketStack(cfn_stack_name_prefix + 'acceptance-test-infrastructure-deployment-assets', logger,
                              boto_session)

    stack.ensure_exists()

    return stack.bucket_name
