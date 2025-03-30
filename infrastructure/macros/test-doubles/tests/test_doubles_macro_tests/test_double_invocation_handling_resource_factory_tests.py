import json
import os
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_lambda import LambdaClient

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from infrastructure_test_support.digest_utils import calculate_md5
from infrastructure_test_support.s3_utils import sync_file_to_s3
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from test_doubles_macro.test_double_invocation_handling_resource_factory import \
    TestDoubleInvocationHandlingResourceFactory

ANY_S3_BUCKET_NAME = 'any-s3-bucket'
ANY_S3_KEY = 'any/s3/key'


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session,
               system_command_executor: SystemCommandExecutor) -> TestCloudFormationStack:
    test_stack_name = f'{cfn_stack_name_prefix}test-double-invocation-handling-resource-factory'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}-test-assets-bucket', logger, boto_session)
    assets_bucket_stack.ensure_exists()

    project_path = absolute_path_relative_to(__file__, '..', '..', '..', '..', 'invocation-handler')

    system_command_executor.execute([os.path.join(project_path, 'build.sh')])

    code_bundle_path = os.path.join(project_path, 'build', 'code.zip')

    function_code_s3_key = calculate_md5(code_bundle_path) + '.zip'

    assets_bucket_name = assets_bucket_stack.bucket_name

    sync_file_to_s3(
        code_bundle_path,
        assets_bucket_name,
        function_code_s3_key,
        boto_session.client('s3')
    )

    test_double_invocation_handling_resource_factory = TestDoubleInvocationHandlingResourceFactory(
        assets_bucket_name,
        function_code_s3_key
    )

    resources = test_double_invocation_handling_resource_factory.generate_resources(
        'FunctionRole',
        'Queue'
    )

    stack = TestCloudFormationStack(test_stack_name, logger, boto_session)
    stack.ensure_state_is(Resources=dict(
        Function=resources.invocation_handler_function,
        FunctionRole=resources.invocation_handler_function_role,
        Queue=resources.invocation_queue
    ))

    return stack


def test_generates_cloudformation_resources_that_enable_interception_lambda_function_invocation_events(
        test_stack: TestCloudFormationStack, boto_session: Session) -> None:
    lambda_client: LambdaClient = boto_session.client('lambda')

    event = dict(invocationTarget=str(uuid4()), invocationId=str(uuid4()), randomString=str(uuid4()))

    lambda_client.invoke(
        FunctionName=get_cfn_physical_id('Function', test_stack),
        InvocationType='RequestResponse',
        Payload=json.dumps(event)
    )

    invocation_message = wait_for_sqs_message_matching(
        lambda message: message is not None and message['MessageAttributes']['InvocationId']['StringValue'] == \
                        event['invocationId'],
        get_cfn_physical_id('Queue', test_stack),
        boto_session.client('sqs')
    )

    assert invocation_message is not None
    assert invocation_message['MessageAttributes']['InvocationTarget']['StringValue'] == event['invocationTarget']
    assert json.loads(invocation_message['Body'])['event'] == event


def get_cfn_physical_id(logical_id: str, test_stack: TestCloudFormationStack) -> str:
    cloudformation_resource = test_stack.get_stack_resource(logical_id)
    assert cloudformation_resource is not None

    return cloudformation_resource['PhysicalResourceId']
