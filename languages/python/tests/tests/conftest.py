import json
import logging
import os
from logging import Logger
from typing import Dict, cast

import pytest
from boto3 import Session

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="session")
def test_configuration() -> Dict[str, str]:
    configuration_file_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    with open(configuration_file_path, 'r') as f:
        return cast(Dict[str, str], json.load(f))


@pytest.fixture(scope="session")
def aws_profile(test_configuration: Dict[str, str]) -> str:
    return test_configuration['awsProfile']


@pytest.fixture(scope="session")
def cfn_stack_name_prefix(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackNamePrefix']


@pytest.fixture(scope="session")
def cfn_test_stack_name(test_configuration: Dict[str, str]) -> str:
    return test_configuration['cfnStackName']


@pytest.fixture(scope="session")
def logger() -> Logger:
    return logging.getLogger()


@pytest.fixture(scope="session")
def boto_session(aws_profile: str) -> Session:
    return Session(profile_name=aws_profile)


@pytest.fixture(scope="session")
def test_cloudformation_stack(cfn_test_stack_name: str, logger: Logger,
                              boto_session: Session) -> TestCloudFormationStack:
    return TestCloudFormationStack(cfn_test_stack_name, logger, boto_session)


@pytest.fixture(scope="session", autouse=True)
def before_all(test_cloudformation_stack: TestCloudFormationStack) -> None:
    test_cloudformation_stack.ensure_state_is(
        Transform='AWS::Serverless-2016-10-31',
        Resources=dict(
            StateMachineRole=dict(
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
            ),
            PassThroughStateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition=dict(
                        StartAt='SetResult',
                        States=dict(
                            SetResult=dict(Type='Pass', End=True)
                        )
                    ),
                    Role={'Fn::GetAtt': 'StateMachineRole.Arn'}
                )
            ),
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
                    ),
                    Role={'Fn::GetAtt': 'StateMachineRole.Arn'}
                )
            ),
            TimingOutStateMachine=dict(
                Type='AWS::Serverless::StateMachine',
                Properties=dict(
                    Definition=dict(
                        StartAt='Wait',
                        States=dict(
                            Wait=dict(Type="Wait", Seconds=2, End=True)
                        ),
                        TimeoutSeconds=1
                    ),
                    Role={'Fn::GetAtt': 'StateMachineRole.Arn'}
                )
            )
        ),
        Outputs=dict(
            PassThroughStateMachineArn=dict(Value=dict(Ref='PassThroughStateMachine')),
            AddNumbersStateMachineArn=dict(Value=dict(Ref='AddNumbersStateMachine')),
            TimingOutStateMachineArn=dict(Value=dict(Ref='TimingOutStateMachine')),
        )
    )


@pytest.fixture(scope="session")
def test_doubles_template_path() -> str:
    return os.path.join(os.path.dirname(__file__), '../../../../infrastructure/test-doubles.yaml')
