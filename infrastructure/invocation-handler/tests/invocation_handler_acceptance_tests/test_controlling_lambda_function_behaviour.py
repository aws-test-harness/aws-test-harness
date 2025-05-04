import json
import os
from datetime import datetime, timedelta
from logging import Logger
from threading import Thread
from typing import Optional, Any, Dict
from uuid import uuid4

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_lambda.client import LambdaClient

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from infrastructure_test_support.digest_utils import calculate_md5
from infrastructure_test_support.s3_utils import sync_file_to_s3
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from test_double_invocation_handler.test_double_invocation_handling_resource_factory import \
    TestDoubleInvocationHandlingResourceFactory


def test_controlling_lambda_function_result(test_configuration: Dict[str, str], logger: Logger, boto_session: Session,
                                            system_command_executor: SystemCommandExecutor) -> None:
    test_stack_name = test_configuration['cfnStackNamePrefix'] + 'test-double-invocation-handler-tests-acceptance'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}test-assets-bucket', logger, boto_session)
    assets_bucket_stack.ensure_exists()

    project_path = absolute_path_relative_to(__file__, '../../../invocation-handler-code')

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

    test_double_invocation_handling_resource_factory = TestDoubleInvocationHandlingResourceFactory(
        assets_bucket_name, function_code_s3_key
    )

    invocation_handling_resources = test_double_invocation_handling_resource_factory.generate_resources(
        invocation_handler_function_role_logical_id='FunctionRole',
        invocation_queue_logical_id='Queue',
        invocation_table_logical_id='Table'
    )

    test_stack = TestCloudFormationStack(test_stack_name, logger, boto_session)
    test_stack.ensure_state_is(
        Resources=dict(
            FunctionRole=invocation_handling_resources.invocation_handler_function_role,
            Function=invocation_handling_resources.invocation_handler_function,
            Queue=invocation_handling_resources.invocation_queue,
            Table=invocation_handling_resources.invocation_table
        )
    )

    invocation_id = str(uuid4())
    random_input_string = str(uuid4())

    lambda_client: LambdaClient = boto_session.client('lambda')
    invocation_handler_function_name = test_stack.get_stack_resource_physical_id('Function')
    event = dict(
        invocationTarget=str(uuid4()),
        invocationId=invocation_id,
        randomString=random_input_string
    )

    lambda_invocation_result_data: Optional[Dict[str, Any]] = None
    lambda_invocation_thread_exception: Optional[BaseException] = None

    def invoke_lambda_function() -> None:
        nonlocal lambda_invocation_result_data, lambda_invocation_thread_exception

        try:
            lambda_invocation_response = lambda_client.invoke(
                FunctionName=invocation_handler_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event)
            )
            lambda_invocation_result_data = json.loads(lambda_invocation_response['Payload'].read().decode('utf-8'))
        except BaseException as e:
            logger.exception('Uncaught exception in invocation-handling thread', exc_info=e)
            lambda_invocation_thread_exception = e

    lambda_invocation_thread = Thread(target=invoke_lambda_function, daemon=True)
    lambda_invocation_thread.start()

    invocation_queue_url = test_stack.get_stack_resource_physical_id('Queue')
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
    invocation_table = dynamodb_resource.Table(test_stack.get_stack_resource_physical_id('Table'))
    sqs_client = boto_session.client('sqs')
    random_output_string = str(uuid4())

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

    lambda_invocation_thread.join()
    assert lambda_invocation_thread_exception is None
    assert lambda_invocation_result_data == dict(randomString=random_output_string)

    assert invocation_message is not None
    assert invocation_message['MessageAttributes']['InvocationTarget']['StringValue'] == event['invocationTarget']
    assert json.loads(invocation_message['Body']) == dict(event=event)
