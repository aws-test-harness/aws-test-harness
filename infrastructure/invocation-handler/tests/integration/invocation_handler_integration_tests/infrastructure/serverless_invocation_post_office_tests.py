import json
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_sqs.type_defs import MessageTypeDef

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from test_double_invocation_handler.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(
        f'{cfn_stack_name_prefix}serverless-invocation-post-office',
        logger,
        boto_session
    )
    stack.ensure_state_is(
        Resources=dict(
            Queue=dict(Type='AWS::SQS::Queue')
        )
    )

    return stack


@pytest.fixture(scope="module")
def received_message(boto_session: Session, test_stack: TestCloudFormationStack) -> MessageTypeDef:
    queue_url = test_stack.get_stack_resource_physical_id('Queue')

    invocation_post_office = ServerlessInvocationPostOffice(queue_url, boto_session)

    unique_invocation_id = str(uuid4())

    invocation_post_office.post_invocation(
        'the-invocation-target',
        unique_invocation_id,
        dict(colour='orange', size='small')
    )

    matching_message = wait_for_sqs_message_matching(
        lambda message: message is not None and
                        message['MessageAttributes']['InvocationId']['StringValue'] == unique_invocation_id,
        queue_url,
        boto_session.client('sqs')
    )

    assert matching_message is not None
    return matching_message


def test_sends_event_data_to_specified_sqs_queue(received_message: MessageTypeDef) -> None:
    assert json.loads(received_message['Body'])['event'] == dict(colour='orange', size='small')


def test_includes_invocation_target_in_sqs_message_attributes(received_message: MessageTypeDef) -> None:
    assert received_message['MessageAttributes']['InvocationTarget']['StringValue'] == 'the-invocation-target'
