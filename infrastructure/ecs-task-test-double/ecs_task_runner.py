#!/usr/bin/env python3
"""
Minimal ECS task runner for AWS Test Harness ECS task mocking.
This script runs inside ECS containers to participate in the mocking framework.
"""

import json
import os
import sys
import boto3
from uuid import uuid4


def main():
    print("ECS Task Runner starting...")
    
    events_queue_url = os.environ.get('EVENTS_QUEUE_URL')
    test_context_bucket_name = os.environ.get('TEST_CONTEXT_BUCKET_NAME')
    
    print(f"Events queue URL: {events_queue_url}")
    print(f"Test context bucket: {test_context_bucket_name}")
    
    s3 = boto3.client('s3')
    get_object_response = s3.get_object(Bucket=test_context_bucket_name, Key='test-id')
    mocking_session_id = get_object_response['Body'].read().decode('utf-8')
    
    print(f"Mocking session ID: {mocking_session_id}")
    
    sqs = boto3.client('sqs')
    
    message_body = json.dumps({
        'input': {'test': 'data'},
        'invocationId': str(uuid4()),
        'taskFamily': 'DataProcessor'
    })
    
    sqs.send_message(
        QueueUrl=events_queue_url,
        MessageBody=message_body,
        MessageGroupId='DataProcessor',
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
    
    print("ECS Task Runner completed successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()