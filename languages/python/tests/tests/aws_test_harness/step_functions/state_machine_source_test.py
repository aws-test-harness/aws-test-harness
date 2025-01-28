from logging import Logger
from typing import Any, Dict

from aws_test_harness.step_functions.state_machine_source import StateMachineSource

ANY_EXECUTION_INPUT: Dict[str, Any] = {}


def test_provides_object_to_interact_with_state_machine_specified_by_cfn_resource_logical_id(
        logger: Logger, cfn_test_stack_name: str, aws_profile: str
) -> None:
    state_machine_source = StateMachineSource(cfn_test_stack_name, logger, aws_profile)

    state_machine = state_machine_source.get_state_machine('AddNumbersStateMachine')

    execution = state_machine.execute({'firstNumber': 1, 'secondNumber': 2})
    assert execution.output == '3'
