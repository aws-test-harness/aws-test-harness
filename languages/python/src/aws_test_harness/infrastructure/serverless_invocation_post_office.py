from datetime import timedelta, datetime
from logging import Logger
from typing import Optional, Any

from boto3 import Session
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_sqs.service_resource import Queue, SQSServiceResource

from aws_test_harness.domain.invocation import Invocation
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice


class ServerlessInvocationPostOffice(InvocationPostOffice):
    def __init__(self, invocation_queue_url: str, invocation_table_name: str, boto_session: Session, logger: Logger):
        self.__logger = logger
        sqs_resource: SQSServiceResource = boto_session.resource('sqs')
        self.__invocation_queue: Queue = sqs_resource.Queue(invocation_queue_url)

        dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
        self.__invocation_table = dynamodb_resource.Table(invocation_table_name)

    def maybe_collect_invocation(self) -> Optional[Invocation]:
        messages = self.__invocation_queue.receive_messages(
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=1
        )

        if not messages:
            return None

        message = messages[0]

        self.__logger.info(
            f'Invocation message received '
            f'with attributes: {message.message_attributes}, '
            f'and body: {message.body}'
        )
        message.delete()

        return Invocation(
            target=message.message_attributes['InvocationTarget']['StringValue'],
            id=message.message_attributes['InvocationId']['StringValue']
        )

    def post_result(self, invocation_id: str, result: Any) -> None:
        self.__invocation_table.put_item(Item=dict(
            id=invocation_id,
            result=result,
            ttl=int((datetime.now() + timedelta(days=1)).timestamp())
        ))
