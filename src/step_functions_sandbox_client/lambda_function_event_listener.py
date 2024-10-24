import json
import sys
import threading
import traceback
from threading import Thread
from typing import Dict, Callable
from unittest.mock import Mock

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_sqs import SQSClient

from .a_thrown_exception import AThrownException


def handle_uncaught_thread_exception(args):
    print('Uncaught exception in thread')
    print(f"Exception Type: {args.exc_type.__name__}")
    print(f"Exception Message: {args.exc_value}")
    traceback.print_tb(args.exc_traceback)


threading.excepthook = handle_uncaught_thread_exception


class LambdaFunctionEventListener(Thread):
    __mock_lambda_functions_by_physical_id: Dict[str, Mock] = {}
    __mock_lambda_functions_by_logical_id: Dict[str, Mock] = {}
    __stop_waiting: bool = False

    def __init__(self, boto_session: Session, events_queue_url: str, results_queue_url: str,
                 get_mocking_session_id: Callable[[], str]):
        super().__init__(daemon=True)
        self.__sqs_client: SQSClient = boto_session.client('sqs')
        self.__events_queue_url = events_queue_url
        self.__results_queue_url = results_queue_url
        self.__get_mocking_session_id = get_mocking_session_id

    def run(self):
        # noinspection PyBroadException
        try:
            while True:
                print('Waiting for message...')
                result = self.__sqs_client.receive_message(
                    QueueUrl=self.__events_queue_url,
                    AttributeNames=['All'],
                    MessageAttributeNames=['All'],
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                )

                if 'Messages' in result:
                    mocking_session_id = self.__get_mocking_session_id()
                    print(f'Current mocking session id: {mocking_session_id}')

                    for message in result['Messages']:
                        print(f'Message received: {json.dumps(message)}')

                        if message['MessageAttributes']['MockingSessionId']['StringValue'] == mocking_session_id:
                            message_payload = json.loads(message['Body'])

                            lambda_function_event = json.loads(message_payload['event'])
                            lambda_function_invocation_id = message_payload['invocationId']
                            lambda_function_name = message_payload['functionName']
                            lambda_execution_environment_id = message_payload['executionEnvironmentId']
                            message_group_id = message['Attributes']['MessageGroupId']

                            print(f"{lambda_function_name} invocation "
                                  f"from execution environment {lambda_execution_environment_id} "
                                  f"with invocation ID {lambda_function_invocation_id} "
                                  f"received event {lambda_function_event}")

                            mock_lambda_function = self.__mock_lambda_functions_by_physical_id[lambda_function_name]

                            lambda_function_result = mock_lambda_function(lambda_function_event)

                            message_payload = dict(
                                raiseException=False,
                                invocationId=lambda_function_invocation_id,
                                functionName=lambda_function_name,
                                executionEnvironmentId=lambda_execution_environment_id
                            )

                            if isinstance(lambda_function_result, AThrownException):
                                message_payload['raiseException'] = True

                                exception_message = lambda_function_result.message
                                message_payload['exceptionMessage'] = exception_message
                                print(f'Throwing exception with message "{exception_message}"')
                            else:
                                message_payload['result'] = json.dumps(lambda_function_result)
                                print(f'Returning result: {json.dumps(lambda_function_result)}')

                            self.__sqs_client.send_message(
                                QueueUrl=self.__results_queue_url,
                                MessageGroupId=message_group_id,
                                MessageAttributes={
                                    'MockingSessionId': {
                                        'DataType': 'String',
                                        'StringValue': mocking_session_id
                                    }
                                },
                                MessageBody=json.dumps(message_payload)
                            )

                        try:
                            receipt_handle = message['ReceiptHandle']
                            self.__sqs_client.delete_message(
                                QueueUrl=self.__events_queue_url,
                                ReceiptHandle=receipt_handle
                            )
                        except ClientError as e:
                            print(f"Failed to delete message: {e}")

                else:
                    print('No messages received')

                if self.__stop_waiting:
                    print('Stopped waiting for messages')
        except Exception:
            print('Exception thrown whilst waiting for messages')
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"Exception Type: {exc_type.__name__}")
            print(f"Exception Message: {exc_value}")
            traceback.print_tb(exc_traceback)

    def stop(self):
        self.__stop_waiting = True

    def register_function(self, function_physical_resource_id: str, function_logical_resource_id: str,
                          mock_lambda_function: Mock):
        self.__mock_lambda_functions_by_physical_id[function_physical_resource_id] = mock_lambda_function
        self.__mock_lambda_functions_by_logical_id[function_logical_resource_id] = mock_lambda_function

    def get_mock_lambda_function(self, logical_resource_id) -> Mock:
        return self.__mock_lambda_functions_by_logical_id[logical_resource_id]
