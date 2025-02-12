import json
import os
from logging import getLogger
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

lambda_execution_environment_id = os.environ['AWS_LAMBDA_LOG_STREAM_NAME']
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

logger = getLogger()


def handler(event, _):
    invocation_id = str(uuid4())
    get_object_response = s3_client.get_object(Bucket=os.environ['TEST_CONTEXT_BUCKET_NAME'], Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')

    invocation_context = dict(invocationId=invocation_id, mockingSessionId=mocking_session_id)

    logger.info(
        f'Test double invocation started',
        extra=dict(**invocation_context, event=event)
    )

    lambda_function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']

    message_payload = dict(
        event=json.dumps(event),
        functionName=lambda_function_name,
        executionEnvironmentId=lambda_execution_environment_id,
        invocationId=invocation_id
    )

    message_attributes = {
        'MockingSessionId': {
            'DataType': 'String',
            'StringValue': mocking_session_id
        }
    }

    message_group_id = lambda_execution_environment_id

    sqs_client.send_message(
        QueueUrl=os.environ['EVENTS_QUEUE_URL'],
        MessageGroupId=message_group_id,
        MessageBody=json.dumps(message_payload),
        MessageAttributes=message_attributes
    )

    logger.info(
        f'Message sent to events queue',
        extra=dict(
            **invocation_context,
            messagePayload=message_payload,
            messageAttributes=message_attributes,
            messageGroupId=message_group_id
        )
    )

    while True:
        logger.info('Waiting for message...', extra=invocation_context)
        results_queue_url = os.environ['RESULTS_QUEUE_URL']

        result = sqs_client.receive_message(
            QueueUrl=results_queue_url,
            AttributeNames=['All'],
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        if 'Messages' in result:
            for message in result['Messages']:
                logger.info(f'Message received', extra=dict(**invocation_context, receivedMessage=message))

                receipt_handle = message['ReceiptHandle']

                if message['MessageAttributes']['MockingSessionId']['StringValue'] == mocking_session_id:
                    if message['Attributes']['MessageGroupId'] == lambda_execution_environment_id:
                        result_message_payload = json.loads(message['Body'])

                        if result_message_payload['invocationId'] == invocation_id:
                            try:
                                raise_exception = result_message_payload.get('raiseException')

                                if raise_exception:
                                    exception_message = result_message_payload['exceptionMessage']

                                    logger.info(
                                        f'Received message instructs function to throw exception',
                                        extra=dict(
                                            **invocation_context,
                                            exceptionMessage=exception_message,
                                            receivedMessage=message)
                                    )

                                    raise Exception(exception_message)
                                else:
                                    lambda_function_result = json.loads(result_message_payload['result'])

                                    logger.info(
                                        f'Received message instructs function to return result',
                                        extra=dict(
                                            **invocation_context,
                                            result=lambda_function_result,
                                            receivedMessage=message
                                        )
                                    )

                                    return lambda_function_result
                            finally:
                                logger.info(
                                    f'Deleting consumed message',
                                    extra=dict(
                                        **invocation_context,
                                        messageToDelete=message
                                    )
                                )

                                delete_message(receipt_handle, results_queue_url, invocation_context)

                    logger.info(
                        "Message received for a different Lambda function, execution environment or invocation. "
                        "Skipping and making it available to other consumers...",
                        extra=dict(
                            **invocation_context,
                            receivedMessage=message
                        )
                    )

                    # Make message immediately available to other consumers
                    sqs_client.change_message_visibility(
                        QueueUrl=results_queue_url,
                        ReceiptHandle=receipt_handle,
                        VisibilityTimeout=0
                    )
                else:
                    logger.info(
                        f"Encountered message from another mocking session. Deleting...",
                        extra=dict(
                            **invocation_context,
                            messageToDelete=message
                        )
                    )
                    delete_message(receipt_handle, results_queue_url, invocation_context)
        else:
            logger.info('No messages received', invocation_context)


def delete_message(receipt_handle, results_queue_url, invocation_context):
    try:
        sqs_client.delete_message(
            QueueUrl=results_queue_url,
            ReceiptHandle=receipt_handle
        )
    except ClientError as e:
        logger.info(
            f"Failed to delete message",
            extra=dict(**invocation_context, receiptHandle=receipt_handle),
            exc_info=e
        )
