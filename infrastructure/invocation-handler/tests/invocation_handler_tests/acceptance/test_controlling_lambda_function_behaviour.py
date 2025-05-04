import json
import os
from datetime import datetime, timedelta
from logging import Logger
from threading import Thread
from typing import Optional
from uuid import uuid4

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_lambda.client import LambdaClient
from mypy_boto3_sqs.type_defs import MessageTypeDef

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from infrastructure_test_support.digest_utils import calculate_md5
from infrastructure_test_support.s3_utils import sync_file_to_s3
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching


def test_controlling_lambda_function_result(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session,
                                            system_command_executor: SystemCommandExecutor) -> None:
    test_stack_name = f'{cfn_stack_name_prefix}acceptance-tests-'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}test-assets-bucket', logger, boto_session)
    assets_bucket_stack.ensure_exists()

    project_path = absolute_path_relative_to(__file__, '..', '..', '..')

    system_command_executor.execute([
        absolute_path_relative_to(__file__, project_path, 'build.sh')
    ])

    code_bundle_path = os.path.join(project_path, 'build', 'code.zip')

    function_code_s3_key = calculate_md5(code_bundle_path) + '.zip'

    assets_bucket_name = assets_bucket_stack.bucket_name

    sync_file_to_s3(
        code_bundle_path,
        assets_bucket_name,
        function_code_s3_key,
        boto_session.client('s3')
    )

    test_stack = TestCloudFormationStack(test_stack_name, logger, boto_session)
    test_stack.ensure_state_is(
        Resources=dict(
            InvocationHandlerFunctionRole=dict(
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
                                    Resource={'Fn::GetAtt': 'InvocationQueue.Arn'}
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
                                    Resource={'Fn::GetAtt': 'InvocationTable.Arn'}
                                )]
                            )
                        )]
                )
            ),
            InvocationHandlerFunction=dict(
                Type='AWS::Lambda::Function',
                Properties=dict(
                    Runtime='python3.13',
                    Handler='test_double_invocation_handler.index.handler',
                    Environment=dict(Variables=dict(
                        INVOCATION_QUEUE_URL=dict(Ref='InvocationQueue'),
                        INVOCATION_TABLE_NAME=dict(Ref='InvocationTable')
                    )),
                    Code=dict(S3Bucket=assets_bucket_name, S3Key=function_code_s3_key),
                    Role={'Fn::GetAtt': 'InvocationHandlerFunctionRole.Arn'},
                )
            ),
            InvocationQueue=dict(Type='AWS::SQS::Queue'),
            InvocationTable=dict(
                Type='AWS::DynamoDB::Table',
                Properties=dict(
                    BillingMode='PAY_PER_REQUEST',
                    KeySchema=[dict(AttributeName="id", KeyType="HASH")],
                    AttributeDefinitions=[dict(AttributeName="id", AttributeType="S")],
                    TimeToLiveSpecification=dict(AttributeName="ttl", Enabled=True)
                )
            )
        )
    )

    invocation_queue_url = test_stack.get_stack_resource_physical_id('InvocationQueue')
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
    invocation_table = dynamodb_resource.Table(test_stack.get_stack_resource_physical_id('InvocationTable'))
    sqs_client = boto_session.client('sqs')

    invocation_id = str(uuid4())
    random_input_string = str(uuid4())
    random_output_string = str(uuid4())

    invocation_message: Optional[MessageTypeDef] = None

    def handle_invocation() -> None:
        nonlocal invocation_message

        try:
            invocation_message = wait_for_sqs_message_matching(
                lambda message: message is not None and
                                message['MessageAttributes']['InvocationId']['StringValue'] == invocation_id,
                invocation_queue_url,
                sqs_client
            )

            invocation_table.put_item(Item=dict(
                id=invocation_id,
                ttl=int((datetime.now() + timedelta(days=1)).timestamp()),
                result=dict(value=dict(randomString=random_output_string))
            ))
        except BaseException as e:
            logger.exception('Uncaught exception in invocation-handling thread', exc_info=e)

    Thread(target=handle_invocation, daemon=True).start()

    lambda_client: LambdaClient = boto_session.client('lambda')
    invocation_handler_function_name = test_stack.get_stack_resource_physical_id('InvocationHandlerFunction')
    event = dict(
        invocationTarget=str(uuid4()),
        invocationId=invocation_id,
        randomString=random_input_string
    )
    lambda_invocation_response = lambda_client.invoke(
        FunctionName=invocation_handler_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )
    lambda_invocation_result_data = json.loads(lambda_invocation_response['Payload'].read().decode('utf-8'))
    assert lambda_invocation_result_data == dict(randomString=random_output_string)

    assert invocation_message is not None
    assert invocation_message['MessageAttributes']['InvocationTarget']['StringValue'] == event['invocationTarget']
    assert json.loads(invocation_message['Body']) == dict(event=event)
