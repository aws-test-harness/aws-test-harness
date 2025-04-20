import sys
from logging import Logger
from time import sleep
from unittest.mock import Mock
from uuid import uuid4

import pytest

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness.infrastructure.sqs_message_invocation_listener import SqsMessageInvocationListener
from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching

ANY_INVOCATION_TARGET = 'ANY_INVOCATION_TARGET'
ANY_INVOCATION_ID = 'ANY_INVOCATION_ID'
ANY_MESSAGE_BODY = '{}'


def test_listens_for_invocations_arriving_at_post_office(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)
    the_invocation_target = str(uuid4())
    the_invocation_id = str(uuid4())

    # Generator expression that provides None indefinitely after yielding inital Invocation
    invocation_post_office.maybe_collect_invocation.side_effect = (
        Invocation(target=the_invocation_target, id=the_invocation_id) if i == 0 else None
        for i in range(sys.maxsize)
    )
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    received_invocations = []

    def handle_invocation(invocation_target: str, invocation_id: str) -> None:
        received_invocations.append(dict(
            invocationTarget=invocation_target,
            invocationId=invocation_id
        ))

    invocation_listener.listen(handle_invocation)

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


def test_continues_listening_for_additional_invocation_messages_on_queue(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)
    first_invocation_id = str(uuid4())
    second_invocation_id = str(uuid4())

    # Generator expression that provides None indefinitely after yielding Invocations
    invocation_post_office.maybe_collect_invocation.side_effect = (
        Invocation(target=ANY_INVOCATION_TARGET, id=first_invocation_id) if i == 0
        else Invocation(target=ANY_INVOCATION_TARGET, id=second_invocation_id) if i == 1
        else None
        for i in range(sys.maxsize)
    )
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with '
        f'invocationId "{first_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == first_invocation_id
        ) and any(
            invocation for invocation in invocations if invocation['invocationId'] == second_invocation_id
        ),
    )


def test_only_listens_once(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)

    invocation_post_office.maybe_collect_invocation.return_value = Invocation(
        target=ANY_INVOCATION_TARGET,
        id=ANY_INVOCATION_ID
    )
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    first_listener_received_invocations = []
    second_listener_received_invocations = []

    def first_listener_invocation_handler(_: str, invocation_id: str) -> None:
        first_listener_received_invocations.append(dict(invocationId=invocation_id))

    def second_listener_invocation_handler(_: str, invocation_id: str) -> None:
        second_listener_received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(first_listener_invocation_handler)

    with pytest.raises(RuntimeError, match='Task is already scheduled'):
        invocation_listener.listen(second_listener_invocation_handler)

    wait_for_value_matching(
        lambda: first_listener_received_invocations,
        'received invocations',
        lambda invocations: len(invocations) > 0,
    )

    assert len(second_listener_received_invocations) == 0


def test_stops_listening_when_instructed(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)
    pending_invocations = []
    invocation_post_office.maybe_collect_invocation.side_effect = lambda: pending_invocations.pop() if pending_invocations else None
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    first_invocation_id = str(uuid4())

    pending_invocations.append(Invocation(target=ANY_INVOCATION_TARGET, id=first_invocation_id))

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with invocationId "{first_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == first_invocation_id
        )
    )

    invocation_listener.stop()

    second_invocation_id = str(uuid4())

    pending_invocations.append(Invocation(target=ANY_INVOCATION_TARGET, id=second_invocation_id))

    sleep(0.5)

    assert any(
        invocation for invocation in received_invocations if invocation['invocationId'] == second_invocation_id
    ) is False, f'Did not expect to receive second invocation'


def test_can_restart_listening_after_stopping(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)
    pending_invocations = []
    invocation_post_office.maybe_collect_invocation.side_effect = lambda: pending_invocations.pop() if pending_invocations else None
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)
    invocation_listener.stop()

    invocation_listener.listen(handle_invocation)

    the_invocation_id = str(uuid4())

    pending_invocations.append(Invocation(target=ANY_INVOCATION_TARGET, id=the_invocation_id))

    wait_for_value_matching(
        lambda: received_invocations,
        f'received invocations to include invocation with invocationId "{the_invocation_id}"',
        lambda invocations: any(
            invocation for invocation in invocations if invocation['invocationId'] == the_invocation_id
        )
    )


def test_continues_listening_after_exception_thrown_whilst_collecting_invocation(logger: Logger) -> None:
    invocation_post_office = Mock(spec=InvocationPostOffice)
    pending_invocations = []
    raise_exception = False

    def maybe_collect_invocation():
        nonlocal raise_exception

        if raise_exception:
            raise_exception = False
            raise Exception('Simulated exception')

        return pending_invocations.pop() if pending_invocations else None

    invocation_post_office.maybe_collect_invocation.side_effect = maybe_collect_invocation
    invocation_listener = SqsMessageInvocationListener(invocation_post_office, logger)

    received_invocations = []

    def handle_invocation(_: str, invocation_id: str) -> None:
        received_invocations.append(dict(invocationId=invocation_id))

    invocation_listener.listen(handle_invocation)

    raise_exception = True

    the_invocation_id = str(uuid4())

    pending_invocations.append(Invocation(target=ANY_INVOCATION_TARGET, id=the_invocation_id))

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
