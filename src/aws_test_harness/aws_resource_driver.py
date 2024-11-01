from .state_machine import StateMachine


class AWSResourceDriver:
    def __init__(self, cloudformation_stack, boto_session):
        self.__cloudformation_stack = cloudformation_stack
        self.__boto_session = boto_session

    def get_state_machine(self, fully_qualified_cfn_logical_resource_id):
        state_machine_arn = self.__cloudformation_stack.get_physical_resource_id_for(
            fully_qualified_cfn_logical_resource_id
        )
        return StateMachine(state_machine_arn, self.__boto_session)
