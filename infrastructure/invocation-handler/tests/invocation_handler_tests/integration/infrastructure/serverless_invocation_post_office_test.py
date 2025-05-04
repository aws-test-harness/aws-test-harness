import json
from datetime import datetime, timedelta
from logging import Logger
from uuid import uuid4

import pytest
from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from mypy_boto3_sqs.type_defs import MessageTypeDef

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack
from infrastructure_test_support.sqs_utils import wait_for_sqs_message_matching
from invocation_handler_tests.support.builders.invocation_builder import an_invocation_with
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
            Queue=dict(Type='AWS::SQS::Queue'),
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

    serverless_invocation_post_office.post_invocation(an_invocation_with(invocation_id=unique_invocation_id,
                                                                         invocation_target='the-invocation-target',
                                                                         payload=dict(colour='orange', size='small')))

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


def test_retrieves_invocation_result_value_from_specified_dynamodb_table(
        serverless_invocation_post_office: ServerlessInvocationPostOffice, invocation_table: Table) -> None:
    invocation_id = str(uuid4())
    random_string = str(uuid4())

    invocation_table.put_item(Item=dict(
        id=invocation_id,
        ttl=int((datetime.now() + timedelta(days=1)).timestamp()),
        result=dict(value=dict(randomString=random_string))
    ))

    result_value = serverless_invocation_post_office.maybe_collect_result(an_invocation_with(
        invocation_id=invocation_id))

    assert result_value == dict(randomString=random_string)

# TODO: test not finding invocation
# TODO: test supporting None result value
# TODO: test receiving instruction to throw exception instead of returning value
