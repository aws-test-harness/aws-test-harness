import json
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from mypy_boto3_sqs.type_defs import MessageTypeDef

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from test_double_invocation_handler_messaging.test_support.builders.invocation_builder import an_invocation_with
from test_double_invocation_handler_messaging.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice
from test_double_invocation_handler_messaging.infrastructure.test_double_invocation_messaging_resource_factory import \
    TestDoubleInvocationMessagingResourceFactory
from test_double_invocation_handler_messaging.test_support.invocation_messaging_utils import \
    put_invocation_result_dynamodb_record, wait_for_invocation_sqs_message, get_invocation_target_from_sqs_message


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, logger: Logger, boto_session: Session) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(
        f'{cfn_stack_name_prefix}serverless-invocation-post-office',
        logger,
        boto_session
    )
    stack.ensure_state_is(
        Resources=dict(
            Queue=TestDoubleInvocationMessagingResourceFactory.generate_queue_resource(),
            Table=TestDoubleInvocationMessagingResourceFactory.generate_invocations_table()
        )
    )

    return stack


@pytest.fixture(scope="module")
def queue_url(test_stack: TestCloudFormationStack) -> str:
    return test_stack.get_stack_resource_physical_id('Queue')


@pytest.fixture(scope="module")
def table_name(test_stack: TestCloudFormationStack) -> str:
    return test_stack.get_stack_resource_physical_id('Table')


@pytest.fixture(scope="module")
def serverless_invocation_post_office(boto_session: Session, queue_url: str,
                                      table_name: str) -> ServerlessInvocationPostOffice:
    return ServerlessInvocationPostOffice(queue_url, table_name, boto_session)


@pytest.fixture(scope="module")
def invocation_table(boto_session: Session, table_name: str) -> Table:
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
    return dynamodb_resource.Table(table_name)


@pytest.fixture(scope="function")
def received_message(boto_session: Session, queue_url: str,
                     serverless_invocation_post_office: ServerlessInvocationPostOffice) -> MessageTypeDef:
    unique_invocation_id = str(uuid4())

    serverless_invocation_post_office.post_invocation(
        an_invocation_with(
            invocation_id=unique_invocation_id,
            invocation_target='the-invocation-target',
            parameters=dict(colour='orange', size='small')
        )
    )

    matching_message = wait_for_invocation_sqs_message(unique_invocation_id, queue_url, boto_session.client('sqs'))

    assert matching_message is not None
    return matching_message


def test_sends_event_data_to_specified_sqs_queue(received_message: MessageTypeDef) -> None:
    message_payload = json.loads(received_message['Body'])
    assert message_payload['parameters'] == dict(colour='orange', size='small')


def test_includes_invocation_target_in_sqs_message_attributes(received_message: MessageTypeDef) -> None:
    invocation_target = get_invocation_target_from_sqs_message(received_message)
    assert invocation_target == 'the-invocation-target'


def test_retrieves_invocation_result_value_from_specified_dynamodb_table(
        serverless_invocation_post_office: ServerlessInvocationPostOffice, invocation_table: Table) -> None:
    invocation_id = str(uuid4())
    random_string = str(uuid4())

    put_invocation_result_dynamodb_record(invocation_id, dict(value=dict(randomString=random_string)),
                                          invocation_table)

    retrieval_attempt = serverless_invocation_post_office.maybe_collect_result(an_invocation_with(
        invocation_id=invocation_id))

    assert retrieval_attempt.succeeded is True
    assert retrieval_attempt.value == dict(randomString=random_string)


def test_indicates_retrieval_attempt_failed_when_no_invocation_result_table_record_exists(
        serverless_invocation_post_office: ServerlessInvocationPostOffice, invocation_table: Table) -> None:
    invocation_id = str(uuid4())

    retrieval_attempt = serverless_invocation_post_office.maybe_collect_result(an_invocation_with(
        invocation_id=invocation_id))

    assert retrieval_attempt.succeeded is False
