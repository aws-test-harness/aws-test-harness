import json
import hashlib

import boto3

from domain.invocation import Invocation


class SQSInvocationHandlingQueue:

    def __init__(self, events_queue_url, logger):
        super().__init__()
        self.__events_queue_url = events_queue_url
        self.__sqs_client = boto3.client('sqs')
        self.__logger = logger

    def schedule_handling(self, invocation: Invocation):
        invocation_data = dict(
            taskDefinitionArn=invocation.task_definition_arn,
            containerName=invocation.container_name,
            invocationId=invocation.id,
            taskContext=dict(
                commandArgs=invocation.task_context.command_args,
                environmentVariables=invocation.task_context.environment_variables
            ),
        )

        self.__sqs_client.send_message(
            QueueUrl=self.__events_queue_url,
            MessageBody=json.dumps(invocation_data),
            # Hash to ensure length and character safety
            MessageGroupId=self.__sha1(f"{invocation.task_family}-{invocation.container_name}"),
            MessageAttributes={
                'InvocationType': {
                    'StringValue': 'ECS Task Execution',
                    'DataType': 'String'
                },
                'MockingSessionId': {
                    'StringValue': invocation.mocking_session_id,
                    'DataType': 'String'
                }
            }
        )

        self.__logger.info("Invocation scheduled for handling", invocation=invocation_data)

    @staticmethod
    def __sha1(raw_group_id):
        return hashlib.sha1(raw_group_id.encode()).hexdigest()
