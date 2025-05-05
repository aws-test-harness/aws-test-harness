import json
from typing import Dict, Any, cast

from boto3 import Session
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from mypy_boto3_sqs.client import SQSClient

from test_double_invocation_handler_function_code.domain.invocation import Invocation
from test_double_invocation_handler_function_code.domain.invocation_post_office import InvocationPostOffice
from test_double_invocation_handler_function_code.domain.retrieval_attempt import RetrievalAttempt


class ServerlessInvocationPostOffice(InvocationPostOffice):
    def __init__(self, invocation_queue_url: str, invocation_table_name: str, boto_session: Session):
        self.__invocation_queue_url = invocation_queue_url
        self.__sqs_client: SQSClient = boto_session.client('sqs')

        dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
        self.__invocation_table: Table = dynamodb_resource.Table(invocation_table_name)

    def post_invocation(self, invocation: Invocation) -> None:
        self.__sqs_client.send_message(
            QueueUrl=self.__invocation_queue_url,
            MessageBody=json.dumps(dict(event=invocation.payload)),
            MessageAttributes=dict(
                InvocationTarget=dict(StringValue=invocation.target, DataType='String'),
                InvocationId=dict(StringValue=invocation.id, DataType='String'),
            )
        )

    def maybe_collect_result(self, invocation: Invocation) -> RetrievalAttempt:
        get_item_response = self.__invocation_table.get_item(Key=dict(id=invocation.id))
        table_item = get_item_response.get('Item')

        if table_item is None:
            return RetrievalAttempt.failed()

        item = cast(Dict[str, Any], table_item)
        return RetrievalAttempt(item['result']['value'])
