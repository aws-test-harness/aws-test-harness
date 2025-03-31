from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class TestDoubleInvocationHandlingResourceDescriptions:
    invocation_handler_function: Dict[str, Any]
    invocation_handler_function_role: Dict[str, Any]
    invocation_queue: Dict[str, Any]
    invocation_table: Dict[str, Any]


class TestDoubleInvocationHandlingResourceFactory:
    def __init__(self, invocation_handler_function_code_s3_bucket: str,
                 invocation_handler_function_code_s3_key: str):
        self.__invocation_handler_function_code_s3_bucket = invocation_handler_function_code_s3_bucket
        self.__invocation_handler_function_code_s3_key = invocation_handler_function_code_s3_key

    def generate_resources(self, invocation_handler_function_role_logical_id: str,
                           invocation_queue_logical_id: str,
                           invocation_table_logical_id: str) -> TestDoubleInvocationHandlingResourceDescriptions:
        return TestDoubleInvocationHandlingResourceDescriptions(
            invocation_handler_function=self.__generate_function_resource(invocation_handler_function_role_logical_id,
                                                                          invocation_queue_logical_id,
                                                                          invocation_table_logical_id),
            invocation_handler_function_role=self.__generate_function_role_resource(
                invocation_queue_logical_id, invocation_table_logical_id),
            invocation_queue=self.__generate_queue_resource(),
            invocation_table=self.__generate_invocations_table()
        )

    def __generate_function_resource(self, function_role_logical_id: str,
                                     invocation_queue_logical_id: str, invocation_table_logical_id: str) -> Dict[
        str, Any]:
        return dict(
            Type='AWS::Lambda::Function',
            Properties=dict(
                Runtime='python3.13',
                Handler='test_double_invocation_handler.index.handler',
                Environment=dict(
                    Variables=dict(
                        INVOCATION_QUEUE_URL=dict(Ref=invocation_queue_logical_id),
                        INVOCATION_TABLE_NAME=dict(Ref=invocation_table_logical_id)
                    )
                ),
                Code=dict(
                    S3Bucket=self.__invocation_handler_function_code_s3_bucket,
                    S3Key=self.__invocation_handler_function_code_s3_key,
                ),
                Role={'Fn::GetAtt': f'{function_role_logical_id}.Arn'}
            )
        )

    @staticmethod
    def __generate_function_role_resource(invocation_queue_logical_id: str,
                                          invocation_table_logical_id: str) -> Dict[str, Any]:
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
                Policies=[
                    dict(
                        PolicyName='SendMessagesToInvocationQueue',
                        PolicyDocument=dict(
                            Version='2012-10-17',
                            Statement=[dict(
                                Effect='Allow',
                                Action=['sqs:SendMessage'],
                                Resource={'Fn::GetAtt': f'{invocation_queue_logical_id}.Arn'}
                            )]
                        )
                    ),
                    dict(
                        PolicyName='GetRecordsFromInvocationTable',
                        PolicyDocument=dict(
                            Version='2012-10-17',
                            Statement=[dict(
                                Effect='Allow',
                                Action=['dynamodb:GetItem'],
                                Resource={'Fn::GetAtt': f'{invocation_table_logical_id}.Arn'}
                            )]
                        )
                    )
                ]
            )
        )

    @staticmethod
    def __generate_queue_resource() -> Dict[str, Any]:
        return dict(
            Type='AWS::SQS::Queue',
            Properties=dict(MessageRetentionPeriod=60)
        )

    @staticmethod
    def __generate_invocations_table():
        return dict(
            Type='AWS::DynamoDB::Table',
            Properties=dict(
                BillingMode='PAY_PER_REQUEST',
                KeySchema=[dict(AttributeName="id", KeyType="HASH")],
                AttributeDefinitions=[dict(AttributeName="id", AttributeType="S")],
                TimeToLiveSpecification=dict(AttributeName="ttl", Enabled=True)
            )
        )
