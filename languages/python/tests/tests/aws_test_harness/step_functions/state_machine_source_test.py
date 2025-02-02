from logging import Logger
from typing import Any, Dict
from unittest.mock import Mock

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine_source import StateMachineSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack

ANY_EXECUTION_INPUT: Dict[str, Any] = {}


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}state-machine-source-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack) -> None:
    test_stack.ensure_state_is(
        Transform='AWS::Serverless-2016-10-31',
        Resources=dict(
            AddNumbersStateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition=dict(
                        StartAt='SetResult',
                        States=dict(
                            SetResult=dict(
                                Type='Pass',
                                Parameters={'result.$': 'States.MathAdd($.firstNumber, $.secondNumber)'},
                                OutputPath='$.result',
                                End=True
                            )
                        )
                    )
                )
            ),
        ),
        Outputs=dict(AddNumbersStateMachineArn=dict(Value=dict(Ref='AddNumbersStateMachine')))
    )


def test_provides_object_to_interact_with_state_machine_specified_by_cfn_resource_logical_id(
        test_stack: TestCloudFormationStack, logger: Logger, boto_session: Session) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id.side_effect = (
        lambda logical_id: test_stack.get_output_value(f'{logical_id}Arn')
    )

    state_machine_source = StateMachineSource(resource_registry, logger, boto_session)

    state_machine = state_machine_source.get('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.output == '3'
