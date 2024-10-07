import json

from boto3 import Session

from aws_resource_mocking_engine import AWSResourceMockingEngine
from cloudformation_stack import CloudFormationStack
from state_machine import StateMachine


def test_state_machine(mocking_engine: AWSResourceMockingEngine, cloudformation_stack: CloudFormationStack,
                       tester_boto_session: Session):
    input_transformer_function = mocking_engine.mock_a_lambda_function(
        'InputTransformerFunction',
        lambda event: dict(number=event['data']['number'] + 1)
    )

    mocking_engine.start()

    state_machine_arn = cloudformation_stack.get_physical_resource_id_for(
        "ExampleStateMachine::StateMachine"
    )
    state_machine = StateMachine(state_machine_arn, tester_boto_session)

    execution_input = dict(input=dict(data=dict(number=1)))
    final_state = state_machine.execute(execution_input)
    mocking_engine.stop_listening()

    assert json.loads(final_state['output']) == dict(result=dict(number=2))
    input_transformer_function.assert_called_with(dict(data=dict(number=1)))
