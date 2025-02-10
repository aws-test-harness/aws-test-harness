import logging
import os
from logging import Logger
from typing import Dict

import pytest
from boto3 import Session

from aws_test_harness_test_support import load_test_configuration
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from aws_test_harness_tests.support.s3_test_client import S3TestClient


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
def test_double_macro_name(boto_session: Session, system_command_executor: SystemCommandExecutor, logger: Logger,
                           cfn_stack_name_prefix: str) -> str:
    deployment_assets_bucket_stack = TestS3BucketStack(
        f'{cfn_stack_name_prefix}tests-infrastructure-deployment-assets', logger,
        boto_session
    )

    deployment_assets_bucket_stack.ensure_exists()

    macro_name_prefix = 'python-library-tests-'

    system_command_executor.execute(
        [
            os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../../infrastructure/scripts/install.sh')),
            f"{cfn_stack_name_prefix}test-harness-test-infrastructure",
            deployment_assets_bucket_stack.bucket_name,
            'aws-test-harness/infrastructure/',
            macro_name_prefix
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )

    return f'{macro_name_prefix}AWSTestHarness-TestDoubles'
