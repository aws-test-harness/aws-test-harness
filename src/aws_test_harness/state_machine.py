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

    def __wait_execution(self, execution_arn: str):
        while True:
            response = self.__sfn_client.describe_execution(executionArn=execution_arn)
            status = response["status"]
            if status == "SUCCEEDED":
                logging.info(f"Execution {execution_arn} completely successfully.")
                return response
            elif status == "RUNNING":
                logging.info(f"Execution {execution_arn} is still running, waiting")
                sleep(1)
            elif status == "FAILED":
                cause = response["cause"]
                raise Exception(f"Execution {execution_arn} failed with status {status} and cause {cause}")
            else:
                raise Exception(f"Execution {execution_arn} failed with status {status}")
