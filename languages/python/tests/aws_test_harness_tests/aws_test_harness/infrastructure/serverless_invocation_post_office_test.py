from logging import Logger
from typing import cast
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_sqs.client import SQSClient

from aws_test_harness.infrastructure.serverless_invocation_post_office import ServerlessInvocationPostOffice
from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack

ANY_MESSAGE_BODY = '{}'


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}serverless-post-office-test', logger, boto_session)


@pytest.fixture(scope="module")
def sqs_client(boto_session: Session) -> SQSClient:
    return cast(SQSClient, boto_session.client('sqs'))


@pytest.fixture(scope="module")
def sqs_queue_url(test_stack: TestCloudFormationStack) -> str:
    test_stack.ensure_state_is(
        Resources=dict(
            Queue=dict(
                Type='AWS::SQS::Queue',
                Properties=dict(MessageRetentionPeriod=60)
            )
        )
    )

    return test_stack.get_stack_resource_physical_id('Queue')


@pytest.fixture(scope="function")
def invocation_post_office(sqs_queue_url: str, boto_session: Session, logger: Logger) -> ServerlessInvocationPostOffice:
    return ServerlessInvocationPostOffice(sqs_queue_url, self.__test_resource_registry.get_physical_resource_id(
        'AWSTestHarnessTestDoubleInvocationTable'), boto_session, logger)


def test_collects_invocation_from_sqs_queue(invocation_post_office: ServerlessInvocationPostOffice,
                                            sqs_client: SQSClient, sqs_queue_url: str) -> None:
    the_invocation_target = str(uuid4())
    the_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=dict(
            InvocationTarget=dict(DataType='String', StringValue=the_invocation_target),
            InvocationId=dict(DataType='String', StringValue=the_invocation_id)
        )
    )

    wait_for_value_matching(
        invocation_post_office.maybe_collect_invocation,
        f'invocation with target "{the_invocation_target}" and id "{the_invocation_id}"',
        lambda invocation: invocation.target == the_invocation_target and invocation.id == the_invocation_id
    )


def test_returns_none_when_no_invocation_message_found_on_queue(invocation_post_office: ServerlessInvocationPostOffice,
                                                                sqs_client: SQSClient, sqs_queue_url: str) -> None:
    wait_for_value_matching(
        invocation_post_office.maybe_collect_invocation,
        f'None value',
        lambda invocation: invocation is None
    )
