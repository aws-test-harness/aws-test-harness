import json
import os
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
from test_double_invocation_handler_infrastructure.test_double_invocation_handling_resource_factory import \
    TestDoubleInvocationHandlingResourceFactory
from test_double_invocation_handler_messaging.test_support.invocation_messaging_utils import \
    put_invocation_result_dynamodb_record, get_invocation_parameters_from_sqs_message, \
    get_invocation_target_from_sqs_message, wait_for_invocation_sqs_message


def test_handling_invocation(test_configuration: Dict[str, str], logger: Logger, boto_session: Session,
                                            system_command_executor: SystemCommandExecutor) -> None:
    test_stack_name = test_configuration['cfnStackNamePrefix'] + 'test-double-invocation-handler-tests-acceptance'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}test-assets-bucket', logger, boto_session)
    assets_bucket_stack.ensure_exists()

    project_path = absolute_path_relative_to(__file__, '../../../function-code')

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
    invocation_target = str(uuid4())

    lambda_invocation_result_data: Optional[Dict[str, Any]] = None
    lambda_invocation_thread_exception: Optional[BaseException] = None

    def invoke_lambda_function() -> None:
        nonlocal lambda_invocation_result_data, lambda_invocation_thread_exception

        try:
            lambda_invocation_response = lambda_client.invoke(
                FunctionName=invocation_handler_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(dict(
                    invocationTarget=invocation_target,
                    invocationId=invocation_id,
                    invocationParameters=dict(randomString=random_input_string)
                ))
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

    invocation_message = wait_for_invocation_sqs_message(invocation_id, invocation_queue_url, sqs_client)

    put_invocation_result_dynamodb_record(invocation_id, dict(value=dict(randomString=random_output_string)),
                                          invocation_table)

    lambda_invocation_thread.join()
    assert lambda_invocation_thread_exception is None
    assert lambda_invocation_result_data == dict(invocationResult=dict(value=dict(randomString=random_output_string)))

    assert invocation_message is not None
    assert get_invocation_target_from_sqs_message(invocation_message) == invocation_target

    invocation_parameters = get_invocation_parameters_from_sqs_message(invocation_message)
    assert invocation_parameters == dict(randomString=random_input_string)
