import json
import sys
import threading
import traceback

from botocore.exceptions import ClientError


def handle_uncaught_thread_exception(args):
    print('Uncaught exception in thread')
    print(f"Exception Type: {args.exc_type.__name__}")
    print(f"Exception Message: {args.exc_value}")
    traceback.print_tb(args.exc_traceback)


threading.excepthook = handle_uncaught_thread_exception

# TODO: Ensure that (undeleted) messages from previous test runs do not interfere with the current test run
class LambdaFunctionListener(threading.Thread):
    __stop_waiting = False

    def __init__(self, event_queue_url, mock_lambda_function, results_queue_url, sqs_client):
        super().__init__(daemon=True)
        self.__sqs_client = sqs_client
        self.__results_queue_url = results_queue_url
        self.__mock_lambda_function = mock_lambda_function
        self.__event_queue_url = event_queue_url

    def run(self):
        # noinspection PyBroadException
        try:
            while True:
                print('Waiting for message...')
                result = self.__sqs_client.receive_message(
                    QueueUrl=self.__event_queue_url,
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
                        lambda_execution_environment_id = message_payload['executionEnvironmentId']
                        message_group_id = message['Attributes']['MessageGroupId']

                        print(f"{lambda_function_name} invocation "
                              f"from execution environment {lambda_execution_environment_id} "
                              f"with invocation ID {lambda_function_invocation_id} "
                              f"received event {lambda_function_event}")

                        lambda_function_result = self.__mock_lambda_function(lambda_function_event)
                        print(lambda_function_result)

                        message_payload = dict(
                            result=json.dumps(lambda_function_result),
                            invocationId=lambda_function_invocation_id,
                            functionName=lambda_function_name,
                            executionEnvironmentId=lambda_execution_environment_id
                        )

                        self.__sqs_client.send_message(
                            QueueUrl=self.__results_queue_url,
                            MessageGroupId=message_group_id,
                            MessageBody=json.dumps(message_payload)
                        )

                        try:
                            receipt_handle = message['ReceiptHandle']
                            self.__sqs_client.delete_message(
                                QueueUrl=self.__event_queue_url,
                                ReceiptHandle=receipt_handle
                            )
                        except ClientError as e:
                            print(f"Failed to delete message: {e}")
                else:
                    print('No messages received')

                if self.__stop_waiting:
                    print('Stopped waiting for messages')
                    # return
        except Exception:
            print('Exception thrown whilst waiting for messages')
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"Exception Type: {exc_type.__name__}")
            print(f"Exception Message: {exc_value}")
            traceback.print_tb(exc_traceback)

    def stop(self):
        self.__stop_waiting = True
