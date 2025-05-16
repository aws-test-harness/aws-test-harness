from logging import Logger

import pytest
from boto3 import Session

from aws_test_harness.infrastructure.cloudformation_aws_resource_registry import CloudFormationAwsResourceRegistry
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}resource-registry-test', logger, boto_session)


@pytest.fixture(scope="module", autouse=True)
def before_all(test_stack: TestCloudFormationStack) -> None:
    test_stack.ensure_state_is(
        Resources=dict(
            Bucket=dict(Type='AWS::S3::Bucket', Properties={}),
            StateMachine=dict(
                Type='AWS::StepFunctions::StateMachine',
                Properties=dict(
                    Definition=dict(
                        StartAt='SetResult',
                        States=dict(SetResult=dict(Type='Pass', End=True))
                    ),
                    RoleArn={'Fn::GetAtt': 'StateMachineRole.Arn'}
                )
            ),
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
                    ),
                    Policies=[]
                )
            )
        ),
        Outputs=dict(
            BucketArn=dict(Value={'Fn::GetAtt': 'Bucket.Arn'}),
            StateMachineArn=dict(Value={'Fn::GetAtt': 'StateMachine.Arn'}),
        )
    )


def test_provides_arn_for_state_machine_in_stack(test_stack: TestCloudFormationStack, boto_session: Session) -> None:
    state_machine_arn = test_stack.get_output_value('StateMachineArn')
    resource_registry = CloudFormationAwsResourceRegistry(test_stack.name, boto_session)

    retrieved_value = resource_registry.get_resource_arn('StateMachine')

    assert retrieved_value == state_machine_arn


def test_provides_arn_for_s3_bucket_in_stack(test_stack: TestCloudFormationStack, boto_session: Session) -> None:
    bucket_arn = test_stack.get_output_value('BucketArn')
    resource_registry = CloudFormationAwsResourceRegistry(test_stack.name, boto_session)

    retrieved_value = resource_registry.get_resource_arn('Bucket')

    assert retrieved_value == bucket_arn
