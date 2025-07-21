import json
import os
import sys
import boto3
import requests
from time import sleep, time
from uuid import uuid4


def fetch_task_metadata():
    response = requests.get(f"{os.environ['ECS_CONTAINER_METADATA_URI_V4']}/task", timeout=5)
    response.raise_for_status()
    task_metadata = response.json()

    task_family = task_metadata['Family']
    arn_parts = task_metadata['TaskARN'].split(':')
    arn_prefix = ':'.join(arn_parts[:5])
    task_definition_arn = f"{arn_prefix}:task-definition/{task_family}:{task_metadata['Revision']}"

    return task_definition_arn, task_family


def main():
    print("ECS Task Runner starting...")
    
    events_queue_url = os.environ.get('__AWS_TEST_HARNESS__EVENTS_QUEUE_URL')
    test_context_bucket_name = os.environ.get('__AWS_TEST_HARNESS__TEST_CONTEXT_BUCKET_NAME')
    results_table_name = os.environ.get('__AWS_TEST_HARNESS__RESULTS_TABLE_NAME')
    
    s3 = boto3.client('s3')
    get_object_response = s3.get_object(Bucket=test_context_bucket_name, Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')
    
    print(f"Mocking session ID: {mocking_session_id}")
    
    sqs = boto3.client('sqs')
    results_table = boto3.resource('dynamodb').Table(results_table_name)
    
    invocation_id = str(uuid4())
    task_definition_arn, task_family = fetch_task_metadata()

    message_body = json.dumps(dict(
        taskContext=dict(
            commandArgs=sys.argv[1:],
            environmentVariables=dict(os.environ)
        ),
        invocationId=invocation_id,
        taskDefinitionArn=task_definition_arn
    ))
    
    sqs.send_message(
        QueueUrl=events_queue_url,
        MessageBody=message_body,
        MessageGroupId=task_family, # Cannot use task ARN due to constraints on MessageGroupId values
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
    
    print(f"Message sent to events queue with invocaiton ID {invocation_id}: {message_body}")
    print("Polling for result...")
    
    # Poll DynamoDB for the result record with 10-second timeout
    start_time = time()
    timeout_seconds = 10
    
    while True:
        print("Polling for result...")
        
        get_item_result = results_table.get_item(
            Key={'partitionKey': f'{task_definition_arn}#{invocation_id}'}
        )
        
        if 'Item' in get_item_result:
            result = get_item_result['Item']['result']
            exit_code = int(result['exitCode'])
            
            print(f"Found result with exit code: {exit_code}")
            
            if exit_code == 0:
                print("ECS Task Runner completed successfully")
            else:
                print(f"ECS Task Runner failed with exit code: {exit_code}")
            
            sys.exit(exit_code)
        else:
            if time() - start_time > timeout_seconds:
                print(f"Timeout: No result found after {timeout_seconds} seconds")
                sys.exit(1)
            
            print("No result found. Sleeping.")
            sleep(0.2)


if __name__ == "__main__":
    main()