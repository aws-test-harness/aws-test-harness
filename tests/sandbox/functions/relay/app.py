import json
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

sqs_client = boto3.client('sqs')


def handler(event, _):
    invocation_id = str(uuid4())

    lambda_function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']

    message_payload = dict(
        event=json.dumps(event),
        functionName=lambda_function_name,
        executionEnvironmentId=os.environ['AWS_LAMBDA_LOG_STREAM_NAME'],
        invocationId=invocation_id
    )

    sqs_client.send_message(
        QueueUrl=os.environ['EVENTS_QUEUE_URL'],
        MessageGroupId=lambda_function_name,
        MessageBody=json.dumps(message_payload)
    )

    while True:
        print('Waiting for message...')
        results_queue_url = os.environ['RESULTS_QUEUE_URL']

        i = 20
        result = sqs_client.receive_message(
            QueueUrl=results_queue_url,
            MessageSystemAttributeNames=['All'],
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=i,
        )

        if 'Messages' in result:
            for message in result['Messages']:
                print(f'Message received: {message}')
                message_group_id = message['Attributes']['MessageGroupId']

                if message_group_id == lambda_function_name:
                    result_message_payload = json.loads(message['Body'])
                    lambda_execution_environment_id = result_message_payload['executionEnvironmentId']

                    if lambda_execution_environment_id == os.environ['AWS_LAMBDA_LOG_STREAM_NAME']:
                        try:
                            lambda_function_invocation_id = result_message_payload['invocationId']

                            if lambda_function_invocation_id == invocation_id:
                                lambda_function_result = json.loads(result_message_payload['result'])

                                print(f"Result received for {lambda_function_name} invocation "
                                      f"in execution environment {lambda_execution_environment_id} "
                                      f"with invocation ID {lambda_function_invocation_id} : {lambda_function_result}")

                                return lambda_function_result
                        finally:
                            try:
                                receipt_handle = message['ReceiptHandle']
                                print(f"Deleting message {json.dumps(result_message_payload)}...")
                                sqs_client.delete_message(
                                    QueueUrl=results_queue_url,
                                    ReceiptHandle=receipt_handle
                                )
                            except ClientError as e:
                                print(f"Failed to delete message: {e}")
        else:
            print('No messages received')
