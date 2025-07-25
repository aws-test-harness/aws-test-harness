import json
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.file_utils import absolute_path_relative_to
from aws_test_harness_test_support.step_functions_utils import start_state_machine_execution, \
    wait_for_state_machine_execution_completion
from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_double_invocation_handler_messaging.test_support.invocation_messaging_utils import \
    put_invocation_result_dynamodb_record, wait_for_invocation_sqs_message, get_invocation_parameters_from_sqs_message


@pytest.fixture(scope="module", autouse=True)
def install_infrastructure(cfn_stack_name_prefix: str, boto_session: Session,
                           system_command_executor: SystemCommandExecutor,
                           s3_deployment_assets_bucket_name: str) -> None:
    system_command_executor.execute([
        absolute_path_relative_to(__file__, '..', '..', '..', 'scripts', 'build.sh')
    ])

    system_command_executor.execute(
        [
            absolute_path_relative_to(__file__, '..', '..', '..', 'build', 'install.sh'),
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
    red_s3_bucket_resource = test_stack.get_stack_resource('RedAWSTestHarnessS3Bucket')
    assert red_s3_bucket_resource is not None
    assert red_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'

    green_s3_bucket_resource = test_stack.get_stack_resource('GreenAWSTestHarnessS3Bucket')
    assert green_s3_bucket_resource is not None
    assert green_s3_bucket_resource['ResourceType'] == 'AWS::S3::Bucket'


def test_managing_test_double_state_machines(test_stack: TestCloudFormationStack, boto_session: Session) -> None:
    blue_state_machine_resource = test_stack.get_stack_resource('BlueAWSTestHarnessStateMachine')
    assert blue_state_machine_resource is not None
    assert blue_state_machine_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    yellow_state_machine_resource = test_stack.get_stack_resource('YellowAWSTestHarnessStateMachine')
    assert yellow_state_machine_resource is not None
    assert yellow_state_machine_resource['ResourceType'] == 'AWS::StepFunctions::StateMachine'

    step_functions_client: SFNClient = boto_session.client('stepfunctions')

    random_input_string = str(uuid4())
    execution_arn = start_state_machine_execution(
        blue_state_machine_resource['PhysicalResourceId'],
        step_functions_client,
        execution_input=dict(randomString=random_input_string)
    )

    sqs_message = wait_for_invocation_sqs_message(
        execution_arn,
        test_stack.get_stack_resource_physical_id('AWSTestHarnessTestDoubleInvocationQueue'),
        boto_session.client('sqs')
    )

    assert sqs_message is not None
    invocation_parameters = get_invocation_parameters_from_sqs_message(sqs_message)
    assert invocation_parameters['input'] == dict(randomString=random_input_string)

    random_output_string = str(uuid4())
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
    invocation_table = dynamodb_resource.Table(
        test_stack.get_stack_resource_physical_id('AWSTestHarnessTestDoubleInvocationTable'))

    put_invocation_result_dynamodb_record(
        execution_arn,
        dict(status='succeeded', context=dict(result=dict(randomString=random_output_string))),
        invocation_table
    )

    execution_description = wait_for_state_machine_execution_completion(execution_arn, step_functions_client)
    assert execution_description['status'] == 'SUCCEEDED', execution_description['cause']
    assert json.loads(execution_description['output']) == dict(randomString=random_output_string)


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
