from logging import Logger
from typing import Any, Dict
from unittest.mock import Mock

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine_source import StateMachineSource
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack

ANY_EXECUTION_INPUT: Dict[str, Any] = {}


def test_provides_object_to_interact_with_state_machine_specified_by_cfn_resource_logical_id(
        logger: Logger, cfn_test_stack_name: str, aws_profile: str, boto_session: Session,
        test_cloudformation_stack: TestCloudFormationStack
) -> None:
    resource_registry = Mock(spec=ResourceRegistry)
    resource_registry.get_physical_resource_id.side_effect = lambda logical_id: test_cloudformation_stack.get_output_value(f'{logical_id}Arn')
    state_machine_source = StateMachineSource(resource_registry, logger, boto_session)

    state_machine = state_machine_source.get('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.output == '3'
