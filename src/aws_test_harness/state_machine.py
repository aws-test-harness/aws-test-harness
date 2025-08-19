import json
from uuid import uuid4

from boto3 import Session

from aws_test_harness.state_machine_execution import StateMachineExecution


class StateMachine:
    def __init__(self, arn: str, boto_session: Session):
        self.__arn = arn
        self.__sfn_client = boto_session.client('stepfunctions')

    def execute(self, execution_input, timeout_seconds: float = 30):
        execution = self.start_execution(execution_input)
        execution.wait_for_completion(timeout_seconds)

        return execution

    def start_execution(self, execution_input):
        response = self.__sfn_client.start_execution(
            stateMachineArn=self.__arn,
            input=json.dumps(execution_input),
            name=f"test-{uuid4()}"
        )

        return StateMachineExecution(response["executionArn"], self.__sfn_client)

    def send_task_success(self, task_token: str, output: object) -> None:
        self.__sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps(output)
        )

    def send_task_failure(self, task_token: str, error: str, cause: str) -> None:
        self.__sfn_client.send_task_failure(
            taskToken=task_token,
            error=error,
            cause=cause
        )
