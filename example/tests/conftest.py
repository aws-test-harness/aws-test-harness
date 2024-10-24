import json
import os

import pytest

from step_functions_sandbox_client.aws_resource_mocking_engine import AWSResourceMockingEngine
from step_functions_sandbox_client.aws_test_double_driver import AWSTestDoubleDriver
from step_functions_sandbox_client.test_resources_factory import TestResourcesFactory


@pytest.fixture(scope="session")
def test_resources_factory():
    configuration_file_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    with open(configuration_file_path, 'r') as f:
        configuration = json.load(f)

    return TestResourcesFactory(configuration['sandboxStackName'], configuration['awsProfile'])


@pytest.fixture(scope="session")
def resource_driver(test_resources_factory):
    return test_resources_factory.resource_driver


@pytest.fixture(scope="session")
def mocking_engine(test_resources_factory):
    return test_resources_factory.mocking_engine


@pytest.fixture(scope="session")
def test_double_driver(test_resources_factory):
    return test_resources_factory.test_double_driver


@pytest.fixture(scope="function", autouse=True)
def reset_mocking_engine(mocking_engine: AWSResourceMockingEngine):
    mocking_engine.reset()
