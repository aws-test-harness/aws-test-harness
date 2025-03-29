from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TestDoubleStateMachineResourceDescriptions:
    state_machine: Dict[str, Any]
    role: Dict[str, Any]


class TestDoubleStateMachineResourceFactory:

    @classmethod
    def generate_resources(cls, role_cfn_logical_id: str,
                           invocation_handler_function_cfn_logical_id: str) -> TestDoubleStateMachineResourceDescriptions:
        return TestDoubleStateMachineResourceDescriptions(
            state_machine=cls.__generate_state_machine_resource(
                role_cfn_logical_id, invocation_handler_function_cfn_logical_id
            ),
            role=cls.__generate_iam_role_resource(invocation_handler_function_cfn_logical_id)
        )

    @staticmethod
    def __generate_state_machine_resource(role_cfn_logical_id: str, invocation_handler_function_cfn_logical_id: str) -> \
            Dict[str, Any]:
        return dict(
            Type='AWS::StepFunctions::StateMachine',
            Properties=dict(
                RoleArn={'Fn::GetAtt': f'{role_cfn_logical_id}.Arn'},
                DefinitionSubstitutions=dict(
                    InvocationHandlerFunctionName=dict(Ref=invocation_handler_function_cfn_logical_id)
                ),
                Definition=dict(
                    StartAt='GetStateMachineResult',
                    States=dict(GetStateMachineResult=dict(
                        Type='Task',
                        Resource='arn:aws:states:::lambda:invoke',
                        OutputPath='$.Payload',
                        Parameters=dict(
                            Payload={
                                'invocationId.$': '$$.Execution.Id',
                                'invocationTarget.$': '$$.StateMachine.Id',
                                'executionInput.$': '$$.Execution.Input',
                            },
                            FunctionName='${InvocationHandlerFunctionName}'
                        ),
                        End=True
                    ))
                )
            )
        )

    @staticmethod
    def __generate_iam_role_resource(invocations_handler_function_cfn_logical_id: str) -> Dict[str, Any]:
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
                ),
                Policies=[dict(
                    PolicyName='InvokeInvocationHandlerFunction',
                    PolicyDocument=dict(
                        Version='2012-10-17',
                        Statement=[dict(
                            Effect='Allow',
                            Action='lambda:InvokeFunction',
                            Resource={'Fn::GetAtt': f'{invocations_handler_function_cfn_logical_id}.Arn'}
                        )]
                    )
                )]
            )
        )
