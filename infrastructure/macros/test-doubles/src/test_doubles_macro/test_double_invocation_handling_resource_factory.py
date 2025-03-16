from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TestDoubleInvocationHandlingResourceDescriptions:
    invocation_handler_function: Dict[str, Any]
    invocation_handler_function_role: Dict[str, Any]
    invocation_queue: Dict[str, Any]


# TODO: Retrofit tests
class TestDoubleInvocationHandlingResourceFactory:
    @classmethod
    def generate_resources(cls, invocation_handler_function_role_logical_id: str,
                           test_double_invocation_queue_logical_id: str) -> TestDoubleInvocationHandlingResourceDescriptions:
        return TestDoubleInvocationHandlingResourceDescriptions(
            invocation_handler_function=cls.__generate_function_resource(invocation_handler_function_role_logical_id,
                                                                         test_double_invocation_queue_logical_id),
            invocation_handler_function_role=cls.__generate_function_role_resource(
                test_double_invocation_queue_logical_id),
            invocation_queue=cls.__generate_queue_resource()
        )

    @staticmethod
    def __generate_function_resource(invocation_handler_function_role_logical_id: str,
                                     test_double_invocation_queue_logical_id: str) -> Dict[str, Any]:
        return dict(
            Type='AWS::Lambda::Function',
            Properties=dict(
                Runtime='python3.13',
                Handler='index.handler',
                Environment=dict(
                    Variables=dict(INVOCATION_QUEUE_URL=dict(Ref=test_double_invocation_queue_logical_id))
                ),
                Code=dict(
                    # TODO: Support multi-file python source code from dedicated python project and retrofit tests
                    ZipFile='''
import boto3
import json
import os

sqs_client = boto3.client('sqs')


def handler(event, _):
    sqs_client.send_message(
        QueueUrl=os.environ['INVOCATION_QUEUE_URL'],
        MessageBody=json.dumps(dict(event=event)),
        MessageAttributes=dict(InvocationId=dict(StringValue=event['invocationId'], DataType='String'))
    )

    return dict()
'''
                ),
                Role={'Fn::GetAtt': f'{invocation_handler_function_role_logical_id}.Arn'}
            )
        )

    @classmethod
    def __generate_function_role_resource(cls, test_double_invocation_queue_logical_id: str) -> Dict[str, Any]:
        return dict(
            Type='AWS::IAM::Role',
            Properties=dict(
                AssumeRolePolicyDocument=dict(
                    Version='2012-10-17',
                    Statement=[dict(
                        Effect='Allow',
                        Principal=dict(Service='lambda.amazonaws.com'),
                        Action='sts:AssumeRole'
                    )]
                ),
                ManagedPolicyArns=['arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'],
                Policies=[dict(
                    PolicyName='SendMessagesToInvocationQueue',
                    PolicyDocument=dict(
                        Version='2012-10-17',
                        Statement=[dict(
                            Effect='Allow',
                            Action=['sqs:SendMessage'],
                            Resource={'Fn::GetAtt': f'{test_double_invocation_queue_logical_id}.Arn'}
                        )]
                    )
                )]
            )
        )

    @classmethod
    def __generate_queue_resource(cls) -> Dict[str, Any]:
        return dict(Type='AWS::SQS::Queue')
