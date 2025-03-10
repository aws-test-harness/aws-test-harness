from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TestDoubleStateMachineResourceDescriptions:
    state_machine: Dict[str, Any]
    role: Dict[str, Any]


class TestDoubleStateMachineResourceFactory:

    @classmethod
    def generate_resources(cls, role_cfn_logical_id: str) -> TestDoubleStateMachineResourceDescriptions:
        return TestDoubleStateMachineResourceDescriptions(
            state_machine=cls.__generate_state_machine_resource(role_cfn_logical_id),
            role=cls.__generate_iam_role_resource()
        )

    @staticmethod
    def __generate_state_machine_resource(role_cfn_logical_id: str) -> Dict[str, Any]:
        return dict(
            Type='AWS::StepFunctions::StateMachine',
            Properties=dict(
                RoleArn={'Fn::GetAtt': f'{role_cfn_logical_id}.Arn'},
                Definition=dict(
                    StartAt='SetResult',
                    States=dict(SetResult=dict(Type='Pass', End=True))
                )
            )
        )

    @staticmethod
    def __generate_iam_role_resource() -> Dict[str, Any]:
        return dict(
            Type='AWS::IAM::Role',
            Properties=dict(
                AssumeRolePolicyDocument=dict(
                    Version='2012-10-17',
                    Statement=[dict(
                        Effect='Allow',
                        Principal=dict(Service='states.amazonaws.com'),
                        Action='sts:AssumeRole'
                    )]
                )
            )
        )
