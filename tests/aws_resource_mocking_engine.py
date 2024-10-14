import json
import sys
import threading
import traceback
from threading import Thread
from typing import Callable, Dict
from unittest.mock import Mock, create_autospec

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_sqs import SQSClient

from cloudformation_stack import CloudFormationStack


def handle_uncaught_thread_exception(args):
    print('Uncaught exception in thread')
    print(f"Exception Type: {args.exc_type.__name__}")
    print(f"Exception Message: {args.exc_value}")
    traceback.print_tb(args.exc_traceback)


threading.excepthook = handle_uncaught_thread_exception


# TODO: Ensure that (undeleted) messages from previous test runs do not interfere with the current test run
class AWSResourceMockingEngine(Thread):
    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session: Session):
        super().__init__(daemon=True)
        self.__boto_session = boto_session
        self.__cloudformation_stack = cloudformation_stack
        self.__events_queue_url = cloudformation_stack.get_physical_resource_id_for('TestDoubles.LambdaFunctionEventsQueue')
        self.__results_queue_url = cloudformation_stack.get_physical_resource_id_for('TestDoubles.LambdaFunctionResultsQueue')
        self.__mock_lambda_functions: Dict[str, Mock] = {}
        self.__stop_waiting = False

    def reset(self):
        self.__stop_waiting = False
        self.__mock_lambda_functions = {}

    def run(self):
        self.__listen()

    def stop_listening(self):
        self.__stop_waiting = True

    def mock_a_lambda_function(self, logical_resource_id: str,
                               event_handler: Callable[[Dict[str, any]], Dict[str, any]]) -> Mock:
        input_transformer_function_name = self.__cloudformation_stack.get_physical_resource_id_for(
            f'TestDoubles.{logical_resource_id}.Function'
        )

        def lambda_handler(_: Dict[str, any]) -> Dict[str, any]:
            pass

        mock_lambda_function: Mock = create_autospec(lambda_handler, name=logical_resource_id)
        self.__mock_lambda_functions[input_transformer_function_name] = mock_lambda_function
        mock_lambda_function.side_effect = event_handler
        return mock_lambda_function

    def __listen(self):
        # noinspection PyBroadException
        try:
            sqs_client: SQSClient = self.__boto_session.client('sqs')

            while True:
                print('Waiting for message...')
                result = sqs_client.receive_message(
                    QueueUrl=self.__events_queue_url,
                    MessageSystemAttributeNames=['All'],
                    MessageAttributeNames=['All'],
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                )

                if 'Messages' in result:
                    print(json.dumps(result))
                    for message in result['Messages']:
                        message_payload = json.loads(message['Body'])

                        lambda_function_event = json.loads(message_payload['event'])
                        lambda_function_invocation_id = message_payload['invocationId']
                        lambda_function_name = message_payload['functionName']
                        mock_lambda_function = self.__mock_lambda_functions[lambda_function_name]
                        lambda_execution_environment_id = message_payload['executionEnvironmentId']
                        message_group_id = message['Attributes']['MessageGroupId']

                        print(f"{lambda_function_name} invocation "
                              f"from execution environment {lambda_execution_environment_id} "
                              f"with invocation ID {lambda_function_invocation_id} "
                              f"received event {lambda_function_event}")

                        lambda_function_result = mock_lambda_function(lambda_function_event)
                        print(lambda_function_result)

                        message_payload = dict(
                            result=json.dumps(lambda_function_result),
                            invocationId=lambda_function_invocation_id,
                            functionName=lambda_function_name,
                            executionEnvironmentId=lambda_execution_environment_id
                        )

                        sqs_client.send_message(
                            QueueUrl=self.__results_queue_url,
                            MessageGroupId=message_group_id,
                            MessageBody=json.dumps(message_payload)
                        )

                        try:
                            receipt_handle = message['ReceiptHandle']
                            sqs_client.delete_message(
                                QueueUrl=self.__events_queue_url,
                                ReceiptHandle=receipt_handle
                            )
                        except ClientError as e:
                            print(f"Failed to delete message: {e}")
                else:
                    print('No messages received')

                if self.__stop_waiting:
                    print('Stopped waiting for messages')
                    return
        except Exception:
            print('Exception thrown whilst waiting for messages')
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"Exception Type: {exc_type.__name__}")
            print(f"Exception Message: {exc_value}")
            traceback.print_tb(exc_traceback)
