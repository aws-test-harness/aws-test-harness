import boto3
import json
import os

sqs_client = boto3.client('sqs')


def handler(event, _):
    sqs_client.send_message(
        QueueUrl=os.environ['INVOCATION_QUEUE_URL'],
        MessageBody=json.dumps(dict(event=event)),
        MessageAttributes=dict(InvocationId=dict(StringValue=event['invocationId'], DataType='String'))
    )

    return dict()
