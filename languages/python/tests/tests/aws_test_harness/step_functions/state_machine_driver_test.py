import json
from logging import Logger
from typing import Any, Dict

import pytest
from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.step_functions.state_machine_driver import StateMachineDriver
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from tests.support.step_functions_test_client import StepFunctionsTestClient

ANY_EXECUTION_INPUT: Dict[str, Any] = {}


@pytest.fixture(scope="session")
def step_functions_test_client(boto_session: Session) -> StepFunctionsTestClient:
    return StepFunctionsTestClient(boto_session)


def test_executes_state_machine_with_provided_input(boto_session: Session,
                                                        logger: Logger, cloudformation_test_stack_name: str,
                                                        step_functions_test_client: StepFunctionsTestClient,
                                                        test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_arn = test_cloudformation_stack.get_output_value('PassThroughStateMachineArn')
    assert state_machine_arn is not None

    previous_execution_arn = step_functions_test_client.get_latest_execution_arn(state_machine_arn)
    state_machine_driver = StateMachineDriver(ResourceRegistry(boto_session), boto_session, logger)

    execution_input = {
        'aParameter': 'aValue',
        'anotherParameter': {'aNestedParameter': 'anotherValue'}
    }

    state_machine_driver.execute(execution_input, 'PassThroughStateMachine',
                                 cloudformation_test_stack_name)

    new_exection_arn = step_functions_test_client.get_latest_execution_arn(state_machine_arn)
    assert new_exection_arn is not None
    assert new_exection_arn != previous_execution_arn

    execution_input_string = step_functions_test_client.get_execution_input_string(new_exection_arn)
    assert json.loads(execution_input_string) == execution_input

    execution_name = step_functions_test_client.get_execution_name(new_exection_arn)
    assert execution_name.startswith('test-')


def test_reports_execution_success(boto_session: Session,
                                   logger: Logger, cloudformation_test_stack_name: str,
                                   step_functions_test_client: StepFunctionsTestClient,
                                   test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_driver = StateMachineDriver(ResourceRegistry(boto_session), boto_session, logger)

    execution = state_machine_driver.execute(ANY_EXECUTION_INPUT, 'PassThroughStateMachine',
                                             cloudformation_test_stack_name)

    assert execution.status == 'SUCCEEDED'


def test_reports_execution_failure(boto_session: Session,
                                   logger: Logger, cloudformation_test_stack_name: str,
                                   test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_driver = StateMachineDriver(ResourceRegistry(boto_session), boto_session, logger)

    execution_input = {'firstNumber': 1, 'secondNumber': 'NOT A NUMBER'}

    execution = state_machine_driver.execute(execution_input, 'AddNumbersStateMachine',
                                             cloudformation_test_stack_name)

    assert execution.status == 'FAILED'
    assert execution.error == 'States.Runtime'
    assert execution.cause is not None
    assert 'Invalid arguments in States.MathAdd' in execution.cause


def test_reports_execution_timeout(boto_session: Session,
                                   logger: Logger, cloudformation_test_stack_name: str,
                                   test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_driver = StateMachineDriver(ResourceRegistry(boto_session), boto_session, logger)

    execution = state_machine_driver.execute(ANY_EXECUTION_INPUT, 'TimingOutStateMachine',
                                             cloudformation_test_stack_name)

    assert execution.status == 'TIMED_OUT'


def test_provides_execution_result(boto_session: Session,
                                   logger: Logger, cloudformation_test_stack_name: str,
                                   test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_driver = StateMachineDriver(ResourceRegistry(boto_session), boto_session, logger)

    execution_input = {'firstNumber': 1, 'secondNumber': 2}

    execution = state_machine_driver.execute(execution_input, 'AddNumbersStateMachine',
                                             cloudformation_test_stack_name)

    assert execution.output == '3'
