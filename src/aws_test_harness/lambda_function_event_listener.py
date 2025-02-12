import json
import sys
import threading
import traceback
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, Callable, Any

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.service_resource import Table, DynamoDBServiceResource
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
        self.__dynamodb_resource: DynamoDBServiceResource = boto_session.resource('dynamodb')
        self.__test_double_driver = test_double_driver
        self.__get_mocking_session_id = get_mocking_session_id

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
                            # Delete message before processing to prevent other consumers from processing it when the visibility timeout expires
                            # This is necessary in case processing involves a long running operation, e.g. a sleep to control concurrency
                            try:
                                receipt_handle = message['ReceiptHandle']
                                self.__sqs_client.delete_message(
                                    QueueUrl=self.__test_double_driver.events_queue_url,
                                    ReceiptHandle=receipt_handle
                                )
                            except ClientError as e:
                                print(f"Failed to delete message: {e}")

                            message_consumer_thread = Thread(
                                daemon=True,
                                target=self.__consume_message,
                                args=(message, mocking_session_id)
                            )

                            message_consumer_thread.start()

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

    def __consume_message(self, message: Dict[str, Any], mocking_session_id: str) -> None:
        event_message_payload = json.loads(message['Body'])

        function_event = json.loads(event_message_payload['event'])
        function_invocation_id = event_message_payload['invocationId']
        function_name = event_message_payload['functionName']

        print(f"{function_name} invocation with invocation ID {function_invocation_id} "
              f"received event {function_event}")

        event_handler = self.__event_handlers[function_name]

        function_result = event_handler(function_event)

        result = dict(raiseException=False)

        if isinstance(function_result, AThrownException):
            result['raiseException'] = True

            exception_message = function_result.message
            result['exceptionMessage'] = exception_message
            print(f'Throwing exception with message "{exception_message}"')
        else:
            result['payload'] = json.dumps(function_result)
            print(f'Returning result: {json.dumps(function_result)}')

        self.__dynamodb_resource.Table(self.__test_double_driver.results_table_name).put_item(
            Item=dict(
                partitionKey=f'{function_name}#{function_invocation_id}',
                result=result,
                functionName=function_name,
                invocationId=function_invocation_id,
                functionEvent=function_event,
                ttl=int((datetime.now() + timedelta(hours=12)).timestamp())
            )
        )
