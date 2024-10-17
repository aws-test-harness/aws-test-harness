import json
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

lambda_execution_environment_id = os.environ['AWS_LAMBDA_LOG_STREAM_NAME']
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')


def handler(event, _):
    invocation_id = str(uuid4())

    get_object_response = s3_client.get_object(Bucket=os.environ['TEST_CONTEXT_BUCKET_NAME'], Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')
    print(f'Current mocking session id: {mocking_session_id}')

    lambda_function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']

    message_payload = dict(
        event=json.dumps(event),
        functionName=lambda_function_name,
        executionEnvironmentId=lambda_execution_environment_id,
        invocationId=invocation_id
    )

    sqs_client.send_message(
        QueueUrl=os.environ['EVENTS_QUEUE_URL'],
        MessageGroupId=lambda_function_name,
        MessageBody=json.dumps(message_payload),
        MessageAttributes={
            'MockingSessionId': {
                'DataType': 'String',
                'StringValue': mocking_session_id
            }
        }
    )

    while True:
        print('Waiting for message...')
        results_queue_url = os.environ['RESULTS_QUEUE_URL']

        result = sqs_client.receive_message(
            QueueUrl=results_queue_url,
            MessageSystemAttributeNames=['All'],
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        if 'Messages' in result:
            for message in result['Messages']:
                print(f'Message received: {message}')
                receipt_handle = message['ReceiptHandle']

                if message['MessageAttributes']['MockingSessionId']['StringValue'] == mocking_session_id:
                    if message['Attributes']['MessageGroupId'] == lambda_function_name:
                        result_message_payload = json.loads(message['Body'])

                        if result_message_payload['executionEnvironmentId'] == lambda_execution_environment_id:
                            if result_message_payload['invocationId'] == invocation_id:
                                try:
                                    raise_exception = result_message_payload.get('raiseException')

                                    if raise_exception:
                                        exception_message = result_message_payload['exceptionMessage']

                                        print(
                                            f"Exception to throw (with message {exception_message}) received for "
                                            f"{lambda_function_name} invocation in execution environment "
                                            f"{lambda_execution_environment_id} with invocation ID {invocation_id}"
                                        )

                                        raise Exception(exception_message)
                                    else:
                                        lambda_function_result = json.loads(result_message_payload['result'])

                                        print(
                                            f"Result received for {lambda_function_name} invocation "
                                            f"in execution environment {lambda_execution_environment_id} "
                                            f"with invocation ID {invocation_id} : {lambda_function_result}"
                                        )

                                        return lambda_function_result
                                finally:
                                    print(f"Deleting consumed message {json.dumps(result_message_payload)}...")
                                    delete_message(receipt_handle, results_queue_url)

                    print(
                        "Message received for a different Lambda function, execution environment or invocation. "
                        "Skipping and making it available to other consumers..."
                    )

                    # Make message immediately available to other consumers
                    sqs_client.change_message_visibility(
                        QueueUrl=results_queue_url,
                        ReceiptHandle=receipt_handle,
                        VisibilityTimeout=0
                    )
                else:
                    print(f"Encountered message from another test method execution. Deleting...")
                    delete_message(receipt_handle, results_queue_url)
        else:
            print('No messages received')


def delete_message(receipt_handle, results_queue_url):
    try:
        sqs_client.delete_message(
            QueueUrl=results_queue_url,
            ReceiptHandle=receipt_handle
        )
    except ClientError as e:
        print(f"Failed to delete message: {e}")
