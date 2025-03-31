import json
from typing import Dict, Any, cast

from boto3 import Session
from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_dynamodb.service_resource import Table
from mypy_boto3_sqs.client import SQSClient

from test_double_invocation_handler.domain.invocation_post_office import InvocationPostOffice


class ServerlessInvocationPostOffice(InvocationPostOffice):
    def __init__(self, invocation_queue_url: str, invocation_table_name: str, boto_session: Session):
        self.__invocation_queue_url = invocation_queue_url
        self.__sqs_client: SQSClient = boto_session.client('sqs')

        dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
        self.__invocation_table: Table = dynamodb_resource.Table(invocation_table_name)

    def post_invocation(self, invocation_target: str, invocation_id: str, event: Dict[str, Any]) -> None:
        self.__sqs_client.send_message(
            QueueUrl=self.__invocation_queue_url,
            MessageBody=json.dumps(dict(event=event)),
            MessageAttributes=dict(
                InvocationTarget=dict(StringValue=invocation_target, DataType='String'),
                InvocationId=dict(StringValue=invocation_id, DataType='String'),
            )
        )

    def maybe_collect_result(self, invocation_id: str) -> Any:
        get_item_response = self.__invocation_table.get_item(Key=dict(id=invocation_id))
        item = cast(Dict[str, Any], get_item_response['Item'])
        return item['result']['value']
