import json
from logging import Logger

import pytest

from aws_test_harness.step_functions.state_machine_source import StateMachineSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_definition = dict(
        StartAt='SetResult',
        States=dict(
            SetResult=dict(Type='Pass', Parameters={'result.$': '$.input'}, End=True)
        )
    )

    test_cloudformation_stack.ensure_state_is(
        AWSTemplateFormatVersion='2010-09-09',
        Transform='AWS::Serverless-2016-10-31',
        Resources=dict(
            StateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(Definition=state_machine_definition)
            )
        )
    )


def test_detecting_a_successful_step_function_execution(logger: Logger, aws_profile: str,
                                                        cfn_test_stack_name: str) -> None:
    resource_factory = StateMachineSource(cfn_test_stack_name, logger, aws_profile)
    state_machine = resource_factory.get_state_machine('StateMachine')

    execution = state_machine.execute({'input': 'Any input'})

    assert execution.status == 'SUCCEEDED'

    assert execution.output is not None
    assert json.loads(execution.output) == {"result": "Any input"}


def test_detecting_a_failed_step_function_execution(aws_profile: str, cfn_test_stack_name: str,
                                                    logger: Logger) -> None:
    resource_factory = StateMachineSource(cfn_test_stack_name, logger, aws_profile)
    state_machine = resource_factory.get_state_machine('StateMachine')

    execution = state_machine.execute({})

    assert execution.status == 'FAILED'

    cause = execution.cause
    assert cause is not None
    assert "JSONPath '$.input' specified for the field 'result.$' could not be found in the input" in cause

    error = execution.error
    assert error == 'States.Runtime'
