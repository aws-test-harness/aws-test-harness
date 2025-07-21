import json
import sys
import traceback
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, Callable, Any, cast, List

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_sqs import SQSClient

from .a_state_machine_execution_failure import AStateMachineExecutionFailure
from .a_thrown_exception import AThrownException
from .exit_code import ExitCode
from .aws_test_double_driver import AWSTestDoubleDriver


class MessageListener(Thread):
    __event_handlers: Dict[str, Callable[..., Any]] = {}
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

                        # Delete message before processing to prevent other consumers from processing it when the visibility timeout expires
                        # This is necessary in case processing involves a long running operation, e.g. a sleep to control concurrency
                        # Additionally, messages should be deleted regardless of their mocking session ID, to avoid poison pills from previous test runs
                        try:
                            receipt_handle = message['ReceiptHandle']
                            self.__sqs_client.delete_message(
                                QueueUrl=self.__test_double_driver.events_queue_url,
                                ReceiptHandle=receipt_handle
                            )
                        except ClientError as e:
                            print(f"Failed to delete message: {e}")

                        if message['MessageAttributes']['MockingSessionId']['StringValue'] == mocking_session_id:
                            message_consumer_thread = Thread(
                                daemon=True,
                                target=self.__consume_message,
                                args=(message,)
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

    def register_lambda_function_event_handler(self, function_name: str, event_handler):
        handler_id = self.__get_lambda_function_event_handler_id(function_name)
        self.__event_handlers[handler_id] = event_handler

    def register_state_machine_execution_input_handler(
            self,
            state_machine_name: str,
            execution_input_handler: Callable[[Dict[str, any]], Dict[str, any]]
    ):
        handler_id = self.__get_state_machine_execution_input_handler_id(state_machine_name)
        self.__event_handlers[handler_id] = execution_input_handler

    def register_ecs_task_handler(self, task_family: str, task_handler: Callable[[List[str]], ExitCode]):
        handler_id = self.__get_ecs_task_handler_id(task_family)
        self.__event_handlers[handler_id] = task_handler

    def __consume_message(self, message: Dict[str, Any]) -> None:
        event_message_payload = json.loads(message['Body'])

        default_invocation_type = dict(StringValue='Lambda Function Invocation')
        invocation_type = message['MessageAttributes'].get('InvocationType', default_invocation_type)['StringValue']

        if invocation_type == 'State Machine Execution':
            item = self.__generate_result_record_for_state_machine_execution(event_message_payload)
        elif invocation_type == 'Lambda Function Invocation':
            item = self.__generate_result_record_for_lamdba_function_invocation(event_message_payload)
        elif invocation_type == 'ECS Task Execution':
            item = self.__generate_result_record_for_ecs_task_execution(event_message_payload)
        else:
            raise Exception(f'Unknown invocation type: "{invocation_type}"')

        self.__dynamodb_resource.Table(self.__test_double_driver.results_table_name).put_item(Item=item)

    def __generate_result_record_for_lamdba_function_invocation(self, event_message_payload: Dict[str, Any]) -> Dict[
        str, Any]:
        function_event = json.loads(event_message_payload['event'])
        function_invocation_id = event_message_payload['invocationId']
        function_name = event_message_payload['functionName']

        print(f"{function_name} invocation with invocation ID {function_invocation_id} "
              f"received event {function_event}")

        handler_id = self.__get_lambda_function_event_handler_id(function_name)
        event_handler = self.__event_handlers[handler_id]
        event_handler_result = event_handler(function_event)
        assert isinstance(event_handler_result, dict) or isinstance(event_handler_result, AThrownException)

        result: Dict[str, Any] = dict(raiseException=False)

        if isinstance(event_handler_result, AThrownException):
            function_result = cast(AThrownException, event_handler_result)
            result['raiseException'] = True
            result['exceptionMessage'] = function_result.message
        else:
            function_result = cast(Dict[str, Any], event_handler_result)
            result['payload'] = json.dumps(function_result)

        print(f'Returning result: {json.dumps(result)}')

        return dict(
            partitionKey=f'{function_name}#{function_invocation_id}',
            result=result,
            functionName=function_name,
            invocationId=function_invocation_id,
            functionEvent=function_event,
            ttl=int((datetime.now() + timedelta(hours=12)).timestamp())
        )

    def __generate_result_record_for_state_machine_execution(self, event_message_payload: Dict[str, Any]) -> Dict[
        str, Any]:
        execution_input = event_message_payload['input']
        invocation_id = event_message_payload['invocationId']
        state_machine_arn = event_message_payload['stateMachineArn']

        print(f"{state_machine_arn} execution with execution ID {invocation_id} "
              f"received input {execution_input}")

        handler_id = self.__get_state_machine_execution_input_handler_id(state_machine_arn)
        execution_input_handler = self.__event_handlers[handler_id]
        handler_result = execution_input_handler(execution_input)
        assert isinstance(handler_result, dict) or isinstance(handler_result, AStateMachineExecutionFailure)

        result: Dict[str, Any] = dict(failExecution=False)

        if isinstance(handler_result, AStateMachineExecutionFailure):
            state_machine_result = cast(AStateMachineExecutionFailure, handler_result)
            result['failExecution'] = True
            result['error'] = state_machine_result.error
            result['cause'] = state_machine_result.cause
        else:
            state_machine_result = cast(Dict[str, Any], handler_result)
            result['payload'] = json.dumps(state_machine_result)

        print(f'Returning result: {json.dumps(result)}')

        return dict(
            partitionKey=f'{state_machine_arn}#{invocation_id}',
            result=result,
            stateMachineArn=state_machine_arn,
            invocationId=invocation_id,
            input=execution_input,
            ttl=int((datetime.now() + timedelta(hours=12)).timestamp())
        )

    def __generate_result_record_for_ecs_task_execution(self, event_message_payload: Dict[str, Any]) -> Dict[str, Any]:
        command_args = event_message_payload['commandArgs']
        invocation_id = event_message_payload['invocationId']
        task_family = event_message_payload['taskFamily']

        print(f"{task_family} task execution with invocation ID {invocation_id} "
              f"received command args {command_args}")

        handler_id = self.__get_ecs_task_handler_id(task_family)
        task_handler = self.__event_handlers[handler_id]

        task_result = task_handler(command_args)
        assert isinstance(task_result, ExitCode)
        exit_code = cast(ExitCode, task_result)

        result: Dict[str, Any] = dict(exitCode=exit_code.value)
        print(f'Returning result: {json.dumps(result)}')

        return dict(
            partitionKey=f'{task_family}#{invocation_id}',
            result=result,
            taskFamily=task_family,
            invocationId=invocation_id,
            commandArgs=command_args,
            ttl=int((datetime.now() + timedelta(hours=12)).timestamp())
        )

    @staticmethod
    def __get_lambda_function_event_handler_id(function_name: str) -> str:
        return f'LambdaFunction::{function_name}'

    @staticmethod
    def __get_state_machine_execution_input_handler_id(state_machine_name: str) -> str:
        return f'StateMachine::{state_machine_name}'

    @staticmethod
    def __get_ecs_task_handler_id(task_family: str) -> str:
        return f'ECSTask::{task_family}'
