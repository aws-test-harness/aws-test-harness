import json
import sys
import threading
import traceback
from threading import Thread
from typing import Dict, Callable, Any

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_sqs import SQSClient

from .a_thrown_exception import AThrownException
from .aws_test_double_driver import AWSTestDoubleDriver


def handle_uncaught_thread_exception(args):
    print('Uncaught exception in thread')
    print(f"Exception Type: {args.exc_type.__name__}")
    print(f"Exception Message: {args.exc_value}")
    traceback.print_tb(args.exc_traceback)


threading.excepthook = handle_uncaught_thread_exception


class LambdaFunctionEventListener(Thread):
    __event_handlers: Dict[str, Callable[[Dict[str, any]], Any]] = {}
    __stop_waiting: bool = False

    def __init__(self, test_double_driver: AWSTestDoubleDriver, boto_session: Session,
                 get_mocking_session_id: Callable[[], str]):
        super().__init__(daemon=True)
        self.__sqs_client: SQSClient = boto_session.client('sqs')
        self.__test_double_driver = test_double_driver
        self.__get_mocking_session_id = get_mocking_session_id

    # TODO: Move some responsibilities into classes that represent Lambda functions or queues, created by test double driver
    def run(self):
        # noinspection PyBroadException
        try:
            while True:
                print('Waiting for message...')
                result = self.__sqs_client.receive_message(
                    QueueUrl=self.__test_double_driver.events_queue_url,
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

                            function_event = json.loads(message_payload['event'])
                            function_invocation_id = message_payload['invocationId']
                            function_name = message_payload['functionName']
                            function_execution_environment_id = message_payload['executionEnvironmentId']
                            message_group_id = message['Attributes']['MessageGroupId']

                            print(f"{function_name} invocation "
                                  f"from execution environment {function_execution_environment_id} "
                                  f"with invocation ID {function_invocation_id} "
                                  f"received event {function_event}")

                            event_handler = self.__event_handlers[function_name]
                            function_result = event_handler(function_event)

                            message_payload = dict(
                                raiseException=False,
                                invocationId=function_invocation_id,
                                functionName=function_name,
                                executionEnvironmentId=function_execution_environment_id
                            )

                            if isinstance(function_result, AThrownException):
                                message_payload['raiseException'] = True

                                exception_message = function_result.message
                                message_payload['exceptionMessage'] = exception_message
                                print(f'Throwing exception with message "{exception_message}"')
                            else:
                                message_payload['result'] = json.dumps(function_result)
                                print(f'Returning result: {json.dumps(function_result)}')

                            self.__sqs_client.send_message(
                                QueueUrl=self.__test_double_driver.results_queue_url,
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
                                QueueUrl=self.__test_double_driver.events_queue_url,
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

    def register_event_handler(self, function_name: str, event_handler):
        self.__event_handlers[function_name] = event_handler
