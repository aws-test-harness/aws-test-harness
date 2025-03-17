from typing import Dict, Any

import boto3
import json
import os

from mypy_boto3_sqs.client import SQSClient

sqs_client: SQSClient = boto3.client('sqs')


def handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    sqs_client.send_message(
        QueueUrl=os.environ['INVOCATION_QUEUE_URL'],
        MessageBody=json.dumps(dict(event=event)),
        MessageAttributes=dict(InvocationId=dict(StringValue=event['invocationId'], DataType='String'))
    )

    return dict()
