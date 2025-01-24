import json
import logging
from time import sleep
from uuid import uuid4

from boto3 import Session

from aws_test_harness.state_machine_execution import StateMachineExecution


class StateMachine:
    def __init__(self, arn: str, boto_session: Session):
        self.__arn = arn
        self.__sfn_client = boto_session.client('stepfunctions')

    def execute(self, execution_input):
        execution = self.start_execution(execution_input)
        execution.wait_for_completion()

        return execution

    def start_execution(self, execution_input):
        response = self.__sfn_client.start_execution(
            stateMachineArn=self.__arn,
            input=json.dumps(execution_input),
            name=f"test-{uuid4()}"
        )

        return StateMachineExecution(response["executionArn"], self.__sfn_client)
