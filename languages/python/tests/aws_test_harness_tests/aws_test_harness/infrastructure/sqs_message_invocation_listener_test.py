from logging import Logger
from time import sleep
from typing import cast
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_sqs.client import SQSClient

from aws_test_harness.infrastructure.sqs_message_invocation_listener import SqsMessageInvocationListener
from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack

ANY_INVOCATION_TARGET = 'ANY_INVOCATION_TARGET'
ANY_MESSAGE_BODY = '{}'


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    return TestCloudFormationStack(f'{cfn_stack_name_prefix}sqs-message-invocation-listener-test', logger, boto_session)


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
def invocation_listener(sqs_queue_url: str, boto_session: Session, logger: Logger) -> SqsMessageInvocationListener:
    listener = SqsMessageInvocationListener(sqs_queue_url, boto_session, logger)

    yield listener

    listener.stop()


def test_listens_for_invocation_message_on_queue(invocation_listener: SqsMessageInvocationListener,
                                                 sqs_client: SQSClient, sqs_queue_url: str) -> None:
    received_invocations = []

    def handle_invocation(invocation_target: str, invocation_id: str) -> None:
        received_invocations.append(dict(
            invocationTarget=invocation_target,
            invocationId=invocation_id
        ))

    invocation_listener.listen(handle_invocation)

    the_invocation_target = str(uuid4())
    the_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(the_invocation_id, the_invocation_target)
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with '
        f'invocationTarget "{the_invocation_target}" and invocationId "{the_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations
            if invocation['invocationTarget'] == the_invocation_target
            and invocation['invocationId'] == the_invocation_id
        )
    )


def test_continues_listening_for_additional_invocation_messages_on_queue(
        invocation_listener: SqsMessageInvocationListener,
        sqs_client: SQSClient, sqs_queue_url: str) -> None:
    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    first_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(first_invocation_id, ANY_INVOCATION_TARGET)
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with '
        f'invocationId "{first_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == first_invocation_id
        ),
    )

    second_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(second_invocation_id, ANY_INVOCATION_TARGET)
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with '
        f'invocationId "{second_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == first_invocation_id
        )
    )


def test_stops_listening_when_instructed(invocation_listener: SqsMessageInvocationListener,
                                         sqs_client: SQSClient, sqs_queue_url: str) -> None:
    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    first_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(first_invocation_id, ANY_INVOCATION_TARGET),
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with invocationId "{first_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == first_invocation_id
        )
    )

    invocation_listener.stop()

    second_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(second_invocation_id, ANY_INVOCATION_TARGET),
    )

    sleep(0.5)

    assert any(
        invocation for invocation in received_invocations if invocation['invocationId'] == second_invocation_id
    ) is False, f'Did not expect to receive second invocation'


def test_can_restart_listening_after_stopping(invocation_listener: SqsMessageInvocationListener,
                                              sqs_client: SQSClient, sqs_queue_url: str) -> None:
    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)
    invocation_listener.stop()

    invocation_listener.listen(handle_invocation)

    the_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(the_invocation_id, ANY_INVOCATION_TARGET),
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with invocationId "{the_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == the_invocation_id
        )
    )


def test_continues_listening_after_encountering_an_erroneous_message(
        invocation_listener: SqsMessageInvocationListener,
        sqs_client: SQSClient, sqs_queue_url: str) -> None:
    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=dict(
            UnexpectedAttribute=dict(DataType='String', StringValue='any value'),
        )
    )

    the_invocation_id = str(uuid4())

    sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=sqs_message_attributes_for(the_invocation_id, ANY_INVOCATION_TARGET)
    )

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with '
        f'invocationId "{the_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == the_invocation_id
        )
    )


def sqs_message_attributes_for(invocation_id, invocation_target):
    return dict(
        InvocationTarget=dict(DataType='String', StringValue=invocation_target),
        InvocationId=dict(DataType='String', StringValue=invocation_id)
    )
