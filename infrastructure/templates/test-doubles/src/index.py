import json
import os
from logging import getLogger
from time import sleep
from uuid import uuid4

import boto3

sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')
results_table = boto3.resource('dynamodb').Table(os.environ['RESULTS_TABLE_NAME'])
logger = getLogger()

lambda_function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']


def handler(event, _):
    # TODO: Use Lambda function context request ID as invocation ID
    invocation_id = str(uuid4())
    get_object_response = s3_client.get_object(Bucket=os.environ['TEST_CONTEXT_BUCKET_NAME'], Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')

    invocation_context = dict(invocationId=invocation_id, mockingSessionId=mocking_session_id)

    logger.info('Test double invocation started', extra=dict(**invocation_context, event=event))

    message_payload = dict(
        event=json.dumps(event),
        functionName=lambda_function_name,
        invocationId=invocation_id
    )

    message_attributes = {
        'MockingSessionId': {
            'DataType': 'String',
            'StringValue': mocking_session_id
        }
    }

    message_group_id = lambda_function_name

    sqs_client.send_message(
        QueueUrl=os.environ['EVENTS_QUEUE_URL'],
        MessageGroupId=message_group_id,
        MessageBody=json.dumps(message_payload),
        MessageAttributes=message_attributes
    )

    logger.info(
        'Message sent to events queue',
        extra=dict(
            **invocation_context,
            messagePayload=message_payload,
            messageAttributes=message_attributes,
            messageGroupId=message_group_id
        )
    )

    while True:
        logger.info('Polling for result...', extra=invocation_context)

        get_item_result = results_table.get_item(
            Key={'partitionKey': f'{lambda_function_name}#{invocation_id}'},
            ProjectionExpression='#result',
            ExpressionAttributeNames={'#result': 'result'}
        )

        if 'Item' in get_item_result:
            result = get_item_result['Item']['result']

            logger.info('Found result', extra=dict(**invocation_context, result=result))

            raise_exception = result.get('raiseException')

            if raise_exception:
                exception_message = result['exceptionMessage']

                logger.info(
                    'Result instructs function to throw exception',
                    extra=dict(**invocation_context, exceptionMessage=exception_message, result=result)
                )

                raise Exception(exception_message)
            else:
                payload = json.loads(result['payload'])

                logger.info(
                    'Result instructs function to return payload',
                    extra=dict(**invocation_context, payload=payload, result=result)
                )

                return payload

        else:
            logger.info('No result found. Sleeping.', invocation_context)
            sleep(0.2)
