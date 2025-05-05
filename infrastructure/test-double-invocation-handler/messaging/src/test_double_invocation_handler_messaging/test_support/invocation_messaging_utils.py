import json
from datetime import datetime, timedelta
from typing import Any, Dict, cast, Optional

from mypy_boto3_dynamodb.service_resource import Table
from mypy_boto3_sqs import SQSClient
from mypy_boto3_sqs.type_defs import MessageTypeDef

from test_double_invocation_handler_messaging.test_support.sqs_utils import wait_for_sqs_message_matching


def put_invocation_result_dynamodb_record(invocation_id: str, result: Any, invocation_table: Table) -> None:
    invocation_table.put_item(Item=dict(
        id=invocation_id,
        ttl=int((datetime.now() + timedelta(days=1)).timestamp()),
        result=result
    ))


def wait_for_invocation_sqs_message(invocation_id: str, invocation_queue_url: str,
                                    sqs_client: SQSClient) -> Optional[MessageTypeDef]:
    return wait_for_sqs_message_matching(
        lambda message: message is not None and
                        message['MessageAttributes']['InvocationId']['StringValue'] == invocation_id,
        invocation_queue_url,
        sqs_client
    )


def get_invocation_payload_from_sqs_message(invocation_message: MessageTypeDef) -> Dict[str, Any]:
    return cast(Dict[str, Any], json.loads(invocation_message['Body'])['event'])


def get_invocation_target_from_sqs_message(invocation_message: MessageTypeDef) -> str:
    return invocation_message['MessageAttributes']['InvocationTarget']['StringValue']
