import json
from logging import Logger
from os import path
from tempfile import mkdtemp
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_cloudformation.type_defs import StackResourceDetailTypeDef
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.step_functions_utils import wait_for_state_machine_execution_completion, \
    start_statemachine_execution
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_double_invocation_handler_messaging.test_support.invocation_messaging_utils import \
    put_invocation_result_dynamodb_record, wait_for_invocation_sqs_message, get_invocation_parameters_from_sqs_message


@pytest.fixture(scope="module", autouse=True)
def install_infrastructure(cfn_stack_name_prefix: str, boto_session: Session,
                           system_command_executor: SystemCommandExecutor,
                           s3_deployment_assets_bucket_name: str) -> None:
    infrastructure_project_directory_path = absolute_path_relative_to(__file__, '..', '..', '..')

    script_directory_path = path.join(infrastructure_project_directory_path, 'scripts')
    system_command_executor.execute([path.join(script_directory_path, 'build.sh')])
    system_command_executor.execute([path.join(script_directory_path, 'package.sh')])

    temporary_directory_path = mkdtemp()

    system_command_executor.execute([
        'tar', '-C', temporary_directory_path, '-xf',
        path.join(infrastructure_project_directory_path, 'dist', 'infrastructure.tar.gz')
    ])

    system_command_executor.execute(
        [
            path.join(temporary_directory_path, 'install.sh'),
            f"{cfn_stack_name_prefix}infrastructure",
            s3_deployment_assets_bucket_name,
            'aws-test-harness/infrastructure/',
            'infrastructure-tests-'
        ],
        env_vars=dict(AWS_PROFILE=boto_session.profile_name)
    )


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}acceptance', logger, boto_session)

    stack.ensure_state_is(
        Transform=['infrastructure-tests-AWSTestHarness-TestDoubles'],
        Parameters=dict(
            AWSTestHarnessS3Buckets=dict(Type='CommaDelimitedList'),
            AWSTestHarnessStateMachines=dict(Type='CommaDelimitedList'),
        ),
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={})),
        AWSTestHarnessS3Buckets='Red,Green',
        AWSTestHarnessStateMachines='Blue,Yellow'
    )

    return stack


def test_managing_test_double_s3_buckets(test_stack: TestCloudFormationStack) -> None:
    assert_s3_bucket_resource_exists_in(test_stack, 'RedAWSTestHarnessS3Bucket')
    assert_s3_bucket_resource_exists_in(test_stack, 'GreenAWSTestHarnessS3Bucket')


def test_managing_test_double_state_machines(test_stack: TestCloudFormationStack, boto_session: Session) -> None:
    blue_state_machine = assert_state_machine_resource_exists_in(test_stack, 'BlueAWSTestHarnessStateMachine')
    assert_state_machine_resource_exists_in(test_stack, 'YellowAWSTestHarnessStateMachine')

    random_input_string = str(uuid4())

    state_machine_execution = start_statemachine_execution(
        dict(randomString=random_input_string),
        state_machine_arn=blue_state_machine['PhysicalResourceId'],
        boto_session=boto_session
    )

    assert_invocation_present_in_invocation_queue(
        test_stack.get_stack_resource_physical_id('AWSTestHarnessTestDoubleInvocationQueue'),
        expected_execution_arn=state_machine_execution.execution_arn,
        expected_input=dict(randomString=random_input_string),
        boto_session=boto_session
    )

    random_output_string = str(uuid4())

    insert_result_into_invocation_table(
        test_stack.get_stack_resource_physical_id('AWSTestHarnessTestDoubleInvocationTable'),
        execution_arn=state_machine_execution.execution_arn,
        result=dict(randomString=random_output_string),
        boto_session=boto_session
    )

    state_machine_execution.assert_succeeded_with_output(dict(randomString=random_output_string))


def assert_s3_bucket_resource_exists_in(test_stack: TestCloudFormationStack,
                                        resource_logical_id: str) -> StackResourceDetailTypeDef:
    return assert_resource_exists_in_stack(test_stack, resource_logical_id, 'AWS::S3::Bucket')


def assert_state_machine_resource_exists_in(test_stack: TestCloudFormationStack,
                                            resource_logical_id: str) -> StackResourceDetailTypeDef:
    return assert_resource_exists_in_stack(test_stack, resource_logical_id, 'AWS::StepFunctions::StateMachine')


def assert_resource_exists_in_stack(test_stack: TestCloudFormationStack, resource_logical_id: str,
                                    expected_resource_type: str) -> StackResourceDetailTypeDef:
    resource = test_stack.get_stack_resource(resource_logical_id)
    assert resource is not None
    assert resource['ResourceType'] == expected_resource_type

    return resource


def assert_invocation_present_in_invocation_queue(invocation_queue_url: str, expected_execution_arn: str,
                                                  expected_input: dict[str, str], boto_session: Session):
    sqs_message = wait_for_invocation_sqs_message(
        expected_execution_arn,
        invocation_queue_url,
        boto_session.client('sqs')
    )
    assert sqs_message is not None
    invocation_parameters = get_invocation_parameters_from_sqs_message(sqs_message)
    assert invocation_parameters['input'] == expected_input


def test_omitting_test_double_stack_parameters(cfn_stack_name_prefix: str, logger: Logger,
                                               boto_session: Session) -> None:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}acceptance-no-test-doubles', logger, boto_session)

    stack.ensure_state_is(
        Transform=['infrastructure-tests-AWSTestHarness-TestDoubles'],
        Parameters=dict(),
        Resources=dict(Bucket=dict(Type='AWS::S3::Bucket', Properties={}))
    )

    a_stack_resource = stack.get_stack_resource('Bucket')
    assert a_stack_resource is not None


def insert_result_into_invocation_table(invocation_table_name: str, execution_arn: str, result: dict[str, str],
                                        boto_session: Session):
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')

    put_invocation_result_dynamodb_record(
        execution_arn,
        dict(status='succeeded', context=dict(result=result)),
        dynamodb_resource.Table(invocation_table_name)
    )


def assert_state_machine_execution_succeeded_with_output(expected_output: dict[str, str], execution_arn: str,
                                                         step_functions_client: SFNClient):
    execution_description = wait_for_state_machine_execution_completion(execution_arn, step_functions_client)
    assert execution_description['status'] == 'SUCCEEDED', execution_description['cause']
    assert json.loads(execution_description['output']) == expected_output
