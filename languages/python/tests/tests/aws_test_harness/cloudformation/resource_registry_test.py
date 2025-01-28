from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


def test_provides_physical_id_for_resource_specified_by_logical_id(boto_session: Session,
                                                                   cfn_test_stack_name: str,
                                                                   test_cloudformation_stack: TestCloudFormationStack) -> None:
    state_machine_arn = test_cloudformation_stack.get_output_value('PassThroughStateMachineArn')
    resource_registry = ResourceRegistry(cfn_test_stack_name, boto_session)

    physical_id = resource_registry.get_physical_resource_id('PassThroughStateMachine')

    assert physical_id == state_machine_arn
