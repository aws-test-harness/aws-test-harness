import json
import os.path
from logging import Logger

import pytest
from boto3 import Session
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.system_command_executor import SystemCommandExecutor
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from infrastructure_test_support.step_functions_utils import start_state_machine_execution


@pytest.fixture(scope="module", autouse=True)
def install_infrastructure(cfn_stack_name_prefix: str, boto_session: Session,
                           system_command_executor: SystemCommandExecutor,
                           s3_deployment_assets_bucket_name: str) -> None:
    system_command_executor.execute([absolute_path_to('../../../scripts/build.sh')])

    system_command_executor.execute(
        [
            absolute_path_to('../../../build/install.sh'),
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

    invocation_queue_url = test_stack.get_stack_resource_physical_id('AWSTestHarnessTestDoubleInvocationQueue')
    assert invocation_queue_url is not None

    step_functions_client: SFNClient = boto_session.client('stepfunctions')

    execution_arn = start_state_machine_execution(
        blue_state_machine_resource['PhysicalResourceId'],
        step_functions_client,
        execution_input=dict(colour='orange', size='small')
    )

    sqs_message = wait_for_sqs_message_matching(
        lambda message: message['MessageAttributes']['InvocationId']['StringValue'] == execution_arn,
        invocation_queue_url,
        boto_session.client('sqs')
    )

    assert json.loads(sqs_message['Body'])['event']['executionInput'] == dict(colour='orange', size='small')


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


def absolute_path_to(relative_file_path: str) -> str:
    test_double_template_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), relative_file_path))
    return test_double_template_file_path
