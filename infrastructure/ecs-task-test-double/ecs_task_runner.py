import json
import os
import sys
import boto3
from time import sleep, time
from uuid import uuid4


def main():
    print("ECS Task Runner starting...")
    
    events_queue_url = os.environ.get('EVENTS_QUEUE_URL')
    test_context_bucket_name = os.environ.get('TEST_CONTEXT_BUCKET_NAME')
    results_table_name = os.environ.get('RESULTS_TABLE_NAME')
    
    print(f"Events queue URL: {events_queue_url}")
    print(f"Test context bucket: {test_context_bucket_name}")
    print(f"Results table name: {results_table_name}")
    
    s3 = boto3.client('s3')
    get_object_response = s3.get_object(Bucket=test_context_bucket_name, Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')
    
    print(f"Mocking session ID: {mocking_session_id}")
    
    sqs = boto3.client('sqs')
    results_table = boto3.resource('dynamodb').Table(results_table_name)
    
    invocation_id = str(uuid4())
    task_family = os.environ['TASK_FAMILY']
    
    command_args = sys.argv[1:]  # Get command line arguments
    print(f"Command arguments: {command_args}")
    
    task_context = {
        'commandArgs': command_args
    }
    
    message_body = json.dumps({
        'taskContext': task_context,
        'invocationId': invocation_id,
        'taskFamily': task_family
    })
    
    sqs.send_message(
        QueueUrl=events_queue_url,
        MessageBody=message_body,
        MessageGroupId=task_family,
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
    
    print(f"Message sent to events queue with invocaiton ID {invocation_id}, polling for result...")
    
    # Poll DynamoDB for the result record with 10-second timeout
    start_time = time()
    timeout_seconds = 10
    
    while True:
        print("Polling for result...")
        
        get_item_result = results_table.get_item(
            Key={'partitionKey': f'{task_family}#{invocation_id}'}
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