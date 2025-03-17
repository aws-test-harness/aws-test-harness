import hashlib
import json
import os
from logging import Logger
from uuid import uuid4

from boto3 import Session
from mypy_boto3_lambda.client import LambdaClient
from mypy_boto3_sqs.client import SQSClient

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from infrastructure_test_support.s3_utils import sync_file_to_s3
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching


def test_foo(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session,
             system_command_executor: SystemCommandExecutor):
    test_stack_name = f'{cfn_stack_name_prefix}acceptance-tests-'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}-test-assets-bucket', logger, boto_session)
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
                    Policies=[dict(
                        PolicyName='SendMessagesToInvocationQueue',
                        PolicyDocument=dict(
                            Version='2012-10-17',
                            Statement=[dict(
                                Effect='Allow',
                                Action=['sqs:SendMessage'],
                                Resource={'Fn::GetAtt': 'InvocationQueue.Arn'}
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
                    Environment=dict(Variables=dict(INVOCATION_QUEUE_URL=dict(Ref='InvocationQueue'))),
                    Code=dict(S3Bucket=assets_bucket_name, S3Key=function_code_s3_key),
                    Role={'Fn::GetAtt': 'InvocationHandlerFunctionRole.Arn'}
                )
            ),
            InvocationQueue=dict(Type='AWS::SQS::Queue')
        )
    )

    # TODO: delete all other keys from s3 bucket

    invocation_handler_function_name = test_stack.get_stack_resource_physical_id('InvocationHandlerFunction')

    lambda_client: LambdaClient = boto_session.client('lambda')
    random_string = str(uuid4())
    lambda_client.invoke(
        FunctionName=invocation_handler_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(dict(randomString=random_string))
    )

    invocation_message = wait_for_sqs_message_matching(
        lambda message: message['MessageAttributes']['InvocationTarget']['StringValue'] == \
                        invocation_handler_function_name,
        test_stack.get_stack_resource_physical_id('InvocationQueue'),
        boto_session.client('sqs')
    )

    assert json.loads(invocation_message['Body'])['event'] == dict(randomString=random_string)


# TODO: move to a shared module
def calculate_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()
