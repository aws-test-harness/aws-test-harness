import json
import os
import sys
import boto3
import requests
from time import sleep, time
from uuid import uuid4
from datetime import datetime, timezone


class JSONLogger:
    def __init__(self):
        self.task_definition_arn = None
        self.invocation_id = None
        self.mocking_session_id = None

    def set_context(self, task_definition_arn=None, invocation_id=None, mocking_session_id=None):
        if task_definition_arn:
            self.task_definition_arn = task_definition_arn
        if invocation_id:
            self.invocation_id = invocation_id
        if mocking_session_id:
            self.mocking_session_id = mocking_session_id

    def log(self, level, message, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "service": "ecs-task-runner"
        }

        if self.task_definition_arn:
            log_entry["taskDefinitionArn"] = self.task_definition_arn
        if self.invocation_id:
            log_entry["invocationId"] = self.invocation_id
        if self.mocking_session_id:
            log_entry["mockingSessionId"] = self.mocking_session_id

        log_entry.update(kwargs)

        print(json.dumps(log_entry, default=str))

    def info(self, message, **kwargs):
        self.log("INFO", message, **kwargs)

    def error(self, message, **kwargs):
        self.log("ERROR", message, **kwargs)

    def debug(self, message, **kwargs):
        self.log("DEBUG", message, **kwargs)


def fetch_task_metadata():
    container_response = requests.get(f"{os.environ['ECS_CONTAINER_METADATA_URI_V4']}", timeout=5)
    container_response.raise_for_status()
    container_metadata = container_response.json()

    task_response = requests.get(f"{os.environ['ECS_CONTAINER_METADATA_URI_V4']}/task", timeout=5)
    task_response.raise_for_status()
    task_metadata = task_response.json()

    task_family = task_metadata['Family']
    container_name = container_metadata['Name']
    arn_parts = task_metadata['TaskARN'].split(':')
    arn_prefix = ':'.join(arn_parts[:5])
    task_definition_arn = f"{arn_prefix}:task-definition/{task_family}:{task_metadata['Revision']}"

    return task_definition_arn, task_family, container_name


def main():
    logger = JSONLogger()
    logger.info("ECS Task Runner starting")

    events_queue_url = os.environ.get('__AWS_TEST_HARNESS__EVENTS_QUEUE_URL')
    test_context_bucket_name = os.environ.get('__AWS_TEST_HARNESS__TEST_CONTEXT_BUCKET_NAME')
    results_table_name = os.environ.get('__AWS_TEST_HARNESS__RESULTS_TABLE_NAME')

    s3 = boto3.client('s3')
    get_object_response = s3.get_object(Bucket=test_context_bucket_name, Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')

    logger.set_context(mocking_session_id=mocking_session_id)
    logger.info("Retrieved mocking session ID from S3", mockingSessionId=mocking_session_id)

    sqs = boto3.client('sqs')
    results_table = boto3.resource('dynamodb').Table(results_table_name)

    invocation_id = str(uuid4())
    task_definition_arn, task_family, container_name = fetch_task_metadata()

    logger.set_context(task_definition_arn=task_definition_arn, invocation_id=invocation_id)

    message_payload = dict(
        taskContext=dict(commandArgs=sys.argv[1:], environmentVariables=dict(os.environ)),
        invocationId=invocation_id,
        taskDefinitionArn=task_definition_arn,
        containerName=container_name
    )

    sqs.send_message(
        QueueUrl=events_queue_url,
        MessageBody=json.dumps(message_payload),
        MessageGroupId=f"{task_family}-{container_name}",  # Use container-specific ID to allow parallel processing
        MessageAttributes={
            'InvocationType': {
                'StringValue': 'ECS Task Execution',
                'DataType': 'String'
            },
            'MockingSessionId': {
                'StringValue': mocking_session_id,
                'DataType': 'String'
            }
        }
    )

    logger.info("Message sent to events queue",
                messageBody=message_payload,
                queueUrl=events_queue_url,
                messageGroupId=f"{task_family}-{container_name}",
                taskFamily=task_family,
                containerName=container_name)

    # Poll DynamoDB for the result record with 10-second timeout
    start_time = time()
    timeout_seconds = 10

    logger.info("Starting result polling", timeoutSeconds=timeout_seconds)

    while True:
        logger.debug("Polling for result")

        get_item_result = results_table.get_item(
            Key={'partitionKey': f'{task_definition_arn}#{invocation_id}'}
        )

        if 'Item' in get_item_result:
            result = get_item_result['Item']['result']
            exit_code = int(result['exitCode'])

            logger.info("Found result", exitCode=exit_code, result=result)

            if exit_code == 0:
                logger.info("ECS Task Runner completed successfully")
            else:
                logger.error("ECS Task Runner failed", exitCode=exit_code)

            sys.exit(exit_code)
        else:
            if time() - start_time > timeout_seconds:
                logger.error("Timeout: No result found", timeoutSeconds=timeout_seconds)
                sys.exit(1)

            logger.debug("No result found. Sleeping")
            sleep(0.2)


if __name__ == "__main__":
    main()
