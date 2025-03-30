import os
import tempfile
import zipfile
from datetime import datetime
from logging import Logger
from typing import cast, Dict, List, Optional

import pytest
from boto3 import Session
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from aws_test_harness_test_support.test_s3_bucket_stack import TestS3BucketStack
from infrastructure_test_support.digest_utils import calculate_md5
from infrastructure_test_support.s3_utils import sync_file_to_s3
from test_doubles_macro.test_double_resource_factory import TestDoubleResourceFactory

ANY_S3_BUCKET_NAME = 'any-s3-bucket'
ANY_S3_KEY = 'any/s3/key'


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    test_stack_name = f'{cfn_stack_name_prefix}test-double-resource-factory'

    assets_bucket_stack = TestS3BucketStack(f'{test_stack_name}-test-assets-bucket', logger, boto_session)
    assets_bucket_stack.ensure_exists()

    code_bundle_path = get_path_to_any_arbitrary_lambda_code_bundle_zip()
    function_code_s3_key = calculate_md5(code_bundle_path) + '.zip'

    assets_bucket_name = assets_bucket_stack.bucket_name

    sync_file_to_s3(
        code_bundle_path,
        assets_bucket_name,
        function_code_s3_key,
        boto_session.client('s3')
    )

    test_double_resource_factory = TestDoubleResourceFactory(
        assets_bucket_name,
        function_code_s3_key
    )

    desired_test_doubles = create_test_double_parameters_with(
        AWSTestHarnessS3Buckets=['Red', 'Green'],
        AWSTestHarnessStateMachines=['Blue', 'Yellow']
    )

    resources = test_double_resource_factory.generate_additional_resources(desired_test_doubles)

    stack = TestCloudFormationStack(test_stack_name, logger, boto_session)
    stack.ensure_state_is(Resources=resources)

    return stack


@pytest.fixture(scope="module")
def step_functions_client(boto_session: Session) -> SFNClient:
    return cast(SFNClient, boto_session.client('stepfunctions'))


def test_supports_not_specifying_test_doubles() -> None:
    test_double_resource_factory = TestDoubleResourceFactory(ANY_S3_BUCKET_NAME, ANY_S3_KEY)

    resources = test_double_resource_factory.generate_additional_resources(dict())

    assert len(resources) == 0


def test_generates_s3_bucket_cloudformation_resource_for_each_specified_bucket(
        test_stack: TestCloudFormationStack) -> None:
    red_s3_bucket_resource = test_stack.get_stack_resource('RedAWSTestHarnessS3Bucket')
    assert red_s3_bucket_resource is not None
    assert red_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    green_s3_bucket_resource = test_stack.get_stack_resource('GreenAWSTestHarnessS3Bucket')
    assert green_s3_bucket_resource is not None
    assert green_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'


def test_generates_state_machine_cloudformation_resource_for_each_specified_state_machine(
        test_stack: TestCloudFormationStack) -> None:
    blue_s3_bucket_resource = test_stack.get_stack_resource('BlueAWSTestHarnessStateMachine')
    assert blue_s3_bucket_resource is not None
    assert blue_s3_bucket_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    yellow_s3_bucket_resource = test_stack.get_stack_resource('YellowAWSTestHarnessStateMachine')
    assert yellow_s3_bucket_resource is not None
    assert yellow_s3_bucket_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'


def test_generates_invocation_handling_cloudformation_resources(
        test_stack: TestCloudFormationStack) -> None:
    invocation_handler_function_resource = test_stack.get_stack_resource(
        'AWSTestHarnessTestDoubleInvocationHandlerFunction'
    )
    assert invocation_handler_function_resource is not None
    assert invocation_handler_function_resource['ResourceType'] == 'AWS::Lambda::Function'

    invocation_handler_function_role_resource = test_stack.get_stack_resource(
        'AWSTestHarnessTestDoubleInvocationHandlerFunctionRole'
    )
    assert invocation_handler_function_role_resource is not None
    assert invocation_handler_function_role_resource['ResourceType'] == 'AWS::IAM::Role'

    invocation_queue_resource = test_stack.get_stack_resource(
        'AWSTestHarnessTestDoubleInvocationQueue'
    )
    assert invocation_queue_resource is not None
    assert invocation_queue_resource['ResourceType'] == 'AWS::SQS::Queue'


def test_omits_test_double_invocation_handling_cloudformation_resources_if_no_state_machines_specified() -> None:
    desired_test_doubles = create_test_double_parameters_with(AWSTestHarnessStateMachines=[])
    test_double_resource_factory = TestDoubleResourceFactory(ANY_S3_BUCKET_NAME, ANY_S3_KEY)

    resources = test_double_resource_factory.generate_additional_resources(desired_test_doubles)

    assert 'AWSTestHarnessTestDoubleInvocationHandlerFunction' not in resources


def test_generates_single_iam_role_cloudformation_resource_for_use_by_state_machines(
        test_stack: TestCloudFormationStack, step_functions_client: SFNClient) -> None:
    state_machine_role_name = get_cfn_physical_id('AWSTestHarnessStateMachineRole', test_stack)

    blue_state_machine_role_name = get_state_machine_role_name(
        'BlueAWSTestHarnessStateMachine', test_stack, step_functions_client
    )
    assert blue_state_machine_role_name == state_machine_role_name

    yellow_state_machine_role_name = get_state_machine_role_name(
        'YellowAWSTestHarnessStateMachine', test_stack, step_functions_client
    )
    assert yellow_state_machine_role_name == state_machine_role_name


def test_omits_state_machine_role_cloudformation_resource_if_no_state_machines_specified() -> None:
    desired_test_doubles = create_test_double_parameters_with(AWSTestHarnessStateMachines=[])
    test_double_resource_factory = TestDoubleResourceFactory(ANY_S3_BUCKET_NAME, ANY_S3_KEY)

    resources = test_double_resource_factory.generate_additional_resources(desired_test_doubles)

    assert 'AWSTestHarnessStateMachineRole' not in resources


def get_state_machine_role_name(logical_id: str, test_stack: TestCloudFormationStack,
                                step_functions_client: SFNClient) -> str:
    state_machine_arn = get_cfn_physical_id(logical_id, test_stack)
    state_machine_description = step_functions_client.describe_state_machine(stateMachineArn=state_machine_arn)
    arn = state_machine_description['roleArn']
    arn_parts = arn.split(':role/')

    return arn_parts[1]


def get_cfn_physical_id(logical_id: str, test_stack: TestCloudFormationStack) -> str:
    cloudformation_resource = test_stack.get_stack_resource(logical_id)
    assert cloudformation_resource is not None

    return cloudformation_resource['PhysicalResourceId']


# noinspection PyPep8Naming
def create_test_double_parameters_with(AWSTestHarnessS3Buckets: Optional[List[str]] = None,
                                       AWSTestHarnessStateMachines: Optional[List[str]] = None) -> Dict[str, List[str]]:
    return dict(
        AWSTestHarnessS3Buckets=AWSTestHarnessS3Buckets or [],
        AWSTestHarnessStateMachines=AWSTestHarnessStateMachines or []
    )


def get_path_to_any_arbitrary_lambda_code_bundle_zip() -> str:
    _, code_bundle_path = tempfile.mkstemp()

    jan_1_1980_tuple = (1980, 1, 1, 0, 0, 0)

    with zipfile.ZipFile(code_bundle_path, 'w') as zipf:
        zipf.writestr(
            zipfile.ZipInfo('index.py', date_time=jan_1_1980_tuple),
            'any content'
        )

    epoch_to_1980_1_1_seconds = datetime(*jan_1_1980_tuple).timestamp()
    os.utime(code_bundle_path, (epoch_to_1980_1_1_seconds, epoch_to_1980_1_1_seconds))

    return code_bundle_path
