import json
from logging import Logger
from typing import cast, Dict, List, Optional

import pytest
from boto3 import Session
from mypy_boto3_stepfunctions.client import SFNClient

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from test_doubles_macro.test_double_resource_factory import TestDoubleResourceFactory
from infrastructure_test_support.step_functions_utils import start_state_machine_execution


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    desired_test_doubles = create_test_double_parameters_with(
        AWSTestHarnessS3Buckets=['Red', 'Green'],
        AWSTestHarnessStateMachines=['Blue', 'Yellow']
    )

    resources = TestDoubleResourceFactory.generate_additional_resources(desired_test_doubles)

    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}test-double-resource-factory', logger, boto_session)
    stack.ensure_state_is(Resources=resources)

    return stack


@pytest.fixture(scope="module")
def step_functions_client(boto_session: Session) -> SFNClient:
    return cast(SFNClient, boto_session.client('stepfunctions'))


def test_supports_not_specifying_test_doubles() -> None:
    resources = TestDoubleResourceFactory.generate_additional_resources(dict())
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


def test_generates_cloudformation_resources_enabling_runtime_control_of_state_machines(
        test_stack: TestCloudFormationStack, step_functions_client: SFNClient, boto_session: Session) -> None:
    invocation_queue_url = get_cfn_physical_id(
        'AWSTestHarnessTestDoubleInvocationQueue', test_stack
    )
    blue_state_machine_arn = get_cfn_physical_id('BlueAWSTestHarnessStateMachine', test_stack)

    execution_arn = start_state_machine_execution(
        blue_state_machine_arn,
        step_functions_client,
        execution_input=dict(colour='orange', size='small')
    )

    execution_invocation_message = wait_for_sqs_message_matching(
        # TODO: InvocationType and InvocationTarget attributes - test drive at lower level
        lambda message: message['MessageAttributes']['InvocationId']['StringValue'] == execution_arn,
        invocation_queue_url,
        boto_session.client('sqs')
    )

    message_payload = json.loads(execution_invocation_message['Body'])
    assert message_payload['event']['executionInput'] == dict(colour='orange', size='small')


def test_omits_state_machine_role_cloudformation_resource_if_no_state_machines_specified() -> None:
    desired_test_doubles = create_test_double_parameters_with(AWSTestHarnessStateMachines=[])

    resources = TestDoubleResourceFactory.generate_additional_resources(desired_test_doubles)

    assert 'AWSTestHarnessStateMachineRole' not in resources


def test_omits_test_double_invocation_handling_cloudformation_resources_if_no_state_machines_specified() -> None:
    desired_test_doubles = create_test_double_parameters_with(AWSTestHarnessStateMachines=[])

    resources = TestDoubleResourceFactory.generate_additional_resources(desired_test_doubles)

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
