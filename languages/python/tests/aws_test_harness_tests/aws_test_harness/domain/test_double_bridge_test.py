from unittest.mock import Mock

import pytest

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.test_double_bridge import TestDoubleBridge
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException
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


def test_raises_exception_when_asked_to_provide_result_for_invocation_target_that_has_not_been_mocked() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    test_double_bridge = TestDoubleBridge(aws_resource_registry)

    invocation = Invocation(target='the-resource-arn', id='any invocation id')

    with pytest.raises(UnknownInvocationTargetException, match='the-resource-arn'):
        test_double_bridge.get_result_for(invocation)


def test_forgets_mocks_on_reset() -> None:
    aws_resource_registry = mock_class(AwsResourceRegistry)
    when_calling(aws_resource_registry.get_resource_arn).invoke(
        lambda resource_id: 'the-resource-arn' if resource_id == 'the-resource-id' else None
    )

    test_double_bridge = TestDoubleBridge(aws_resource_registry)
    mock = test_double_bridge.get_mock_for('the-resource-id')
    mock.return_value = 'the result'

    test_double_bridge.reset()

    invocation = Invocation(target='the-resource-arn', id='the invocation id')

    with pytest.raises(UnknownInvocationTargetException):
        test_double_bridge.get_result_for(invocation)
