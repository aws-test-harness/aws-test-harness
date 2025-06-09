from typing import Dict, TypeVar, Optional, Any

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_target_twin import InvocationTargetTwin
from aws_test_harness.domain.test_double_state_machine import TestDoubleStateMachine, StateMachineExecutionHandler
from aws_test_harness.domain.unknown_invocation_target_exception import UnknownInvocationTargetException

InvocationTargetTwinType = TypeVar('InvocationTargetTwinType', bound=InvocationTargetTwin)


# TODO: Retrofit tests
class InvocationTargetTwinService:

    def __init__(self, aws_resource_registry: AwsResourceRegistry):
        self.__aws_resource_registry = aws_resource_registry
        self.__twins: Dict[str, InvocationTargetTwin] = dict()

    def reset(self) -> None:
        self.__twins = dict()

    def create_twin_for_state_machine(self, state_machine_name: str,
                                      execution_handler: Optional[
                                          StateMachineExecutionHandler]) -> TestDoubleStateMachine:
        twin = TestDoubleStateMachine(execution_handler)
        self.__add_twin(f'{state_machine_name}AWSTestHarnessStateMachine', twin)
        return twin

    def generate_result_for_invocation(self, invocation: Invocation) -> Any:
        twin = self.__get_twin_for_invocation_target(invocation.target)
        return twin.get_result_for(invocation)

    def __add_twin(self, cfn_logical_resource_id: str, twin: InvocationTargetTwin) -> None:
        invocation_target = self.__aws_resource_registry.get_resource_arn(cfn_logical_resource_id)
        self.__twins[invocation_target] = twin

    def __get_twin_for_invocation_target(self, invocation_target: str) -> InvocationTargetTwin:
        twin = self.__twins.get(invocation_target)

        if twin is None:
            raise UnknownInvocationTargetException(
                f'No digital twin has been configured for invocation target "{invocation_target}"'
            )

        return twin
