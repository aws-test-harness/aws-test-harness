from datetime import datetime, timedelta
from decimal import Decimal
from logging import Logger
from typing import cast
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from mypy_boto3_sqs.client import SQSClient

from aws_test_harness.infrastructure.serverless_invocation_post_office import ServerlessInvocationPostOffice
from aws_test_harness_test_support.eventual_consistency_utils import wait_for_value_matching
from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack

ANY_MESSAGE_BODY = '{}'


@pytest.fixture(scope="module")
def test_stack(cfn_stack_name_prefix: str, boto_session: Session, logger: Logger) -> TestCloudFormationStack:
    stack = TestCloudFormationStack(f'{cfn_stack_name_prefix}serverless-post-office-test', logger, boto_session)

    stack.ensure_state_is(
        Resources=dict(
            Queue=dict(
                Type='AWS::SQS::Queue',
                Properties=dict(MessageRetentionPeriod=60)
            ),
            Table=dict(
                Type='AWS::DynamoDB::Table',
                Properties=dict(
                    BillingMode='PAY_PER_REQUEST',
                    KeySchema=[dict(AttributeName="id", KeyType="HASH")],
                    AttributeDefinitions=[dict(AttributeName="id", AttributeType="S")],
                    TimeToLiveSpecification=dict(AttributeName="ttl", Enabled=True)
                )
            )
        )
    )

    return stack


@pytest.fixture(scope="module")
def invocation_queue_url(test_stack: TestCloudFormationStack) -> str:
    return test_stack.get_stack_resource_physical_id('Queue')


@pytest.fixture(scope="module")
def invocation_table_name(test_stack: TestCloudFormationStack) -> str:
    return test_stack.get_stack_resource_physical_id('Table')


@pytest.fixture(scope="module")
def invocation_table(invocation_table_name: str, boto_session: Session) -> Table:
    dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
    return dynamodb_resource.Table(invocation_table_name)


@pytest.fixture(scope="function")
def invocation_post_office(invocation_queue_url: str, invocation_table_name: str, boto_session: Session,
                           logger: Logger) -> ServerlessInvocationPostOffice:
    return ServerlessInvocationPostOffice(invocation_queue_url, invocation_table_name, boto_session, logger)


def test_collects_invocation_from_sqs_queue(invocation_post_office: ServerlessInvocationPostOffice,
                                            boto_session: Session, invocation_queue_url: str) -> None:
    the_invocation_target = str(uuid4())
    the_invocation_id = str(uuid4())

    sqs_client: SQSClient = boto_session.client('sqs')

    sqs_client.send_message(
        QueueUrl=invocation_queue_url,
        MessageBody=ANY_MESSAGE_BODY,
        MessageAttributes=dict(
            InvocationTarget=dict(DataType='String', StringValue=the_invocation_target),
            InvocationId=dict(DataType='String', StringValue=the_invocation_id)
        )
    )

    wait_for_value_matching(
        invocation_post_office.maybe_collect_invocation,
        f'invocation with target "{the_invocation_target}" and id "{the_invocation_id}"',
        lambda invocation: invocation is not None
                           and invocation.target == the_invocation_target
                           and invocation.id == the_invocation_id
    )


def test_returns_none_when_no_invocation_message_found_on_queue(
        invocation_post_office: ServerlessInvocationPostOffice) -> None:
    wait_for_value_matching(
        invocation_post_office.maybe_collect_invocation,
        'None value',
        lambda invocation: invocation is None
    )


def test_puts_invocation_result_item_in_dynamodb_table(invocation_post_office: ServerlessInvocationPostOffice,
                                                       invocation_table: Table) -> None:
    invocation_id = str(uuid4())
    invocation_post_office.post_result(invocation_id, dict(value='the-result-value'))

    get_item_result = invocation_table.get_item(Key=dict(id=invocation_id))

    assert 'Item' in get_item_result

    assert 'id' in get_item_result['Item']
    assert get_item_result['Item']['id'] == invocation_id

    assert 'result' in get_item_result['Item']
    assert get_item_result['Item']['result'] == dict(value='the-result-value')


def test_expires_invocation_results_after_24_hours(invocation_post_office: ServerlessInvocationPostOffice,
                                                   invocation_table: Table) -> None:
    time_to_live_description = invocation_table.meta.client.describe_time_to_live(TableName=invocation_table.name)
    assert time_to_live_description['TimeToLiveDescription']['TimeToLiveStatus'] == 'ENABLED'

    invocation_id = str(uuid4())
    invocation_post_office.post_result(invocation_id, dict(value='the-result-value'))

    get_item_result = invocation_table.get_item(Key=dict(id=invocation_id))

    assert 'Item' in get_item_result

    ttl_attribute_name = time_to_live_description['TimeToLiveDescription']['AttributeName']
    assert ttl_attribute_name in get_item_result['Item']

    ttl = get_item_result['Item'][ttl_attribute_name]
    ttl_datetime = datetime.fromtimestamp(int(cast(Decimal, ttl)))
    current_datetime = datetime.now()
    assert ttl_datetime - current_datetime < timedelta(days=1, seconds=5)
