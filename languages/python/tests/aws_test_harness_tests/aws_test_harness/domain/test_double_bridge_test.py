from unittest.mock import Mock

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.test_double_bridge import TestDoubleBridge
from aws_test_harness_tests.support.mocking import mock_class, when_calling


def test_creates_unittest_mock_for_specified_invocation_target() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).always_return('any-resource-arn')

    test_double_bridge = TestDoubleBridge(aws_resource_registry)

    mock = test_double_bridge.get_mock_for('the-resource-id')

    assert isinstance(mock, Mock)


def test_generates_invocation_result_using_mock_associated_with_invocation_target() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(
        lambda resource_id: 'the-resource-arn' if resource_id == 'the-resource-id' else None
    )

    test_double_bridge = TestDoubleBridge(aws_resource_registry)
    mock = test_double_bridge.get_mock_for('the-resource-id')
    mock.return_value = 'the result'

    invocation = Invocation(target='the-resource-arn', id='the invocation id')

    result = test_double_bridge.get_result_for(invocation)

    assert result == 'the result'
