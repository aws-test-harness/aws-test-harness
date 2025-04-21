from unittest.mock import Mock

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.test_double_bridge import TestDoubleBridge


def test_creates_unittest_mock_for_specified_invocation_target():
    test_double_bridge = TestDoubleBridge()

    mock = test_double_bridge.get_mock_for('the invocation target')

    assert isinstance(mock, Mock)


def test_provides_invocation_result_using_mock_associated_with_invocation_target():
    test_double_bridge = TestDoubleBridge()
    mock = test_double_bridge.get_mock_for('the invocation target')
    mock.return_value = 'the result'

    invocation = Invocation(target='the invocation target', id='the invocation id')

    result = test_double_bridge.get_result_for(invocation)

    assert result == 'the result'
