import json
import logging
from time import sleep
from uuid import uuid4

from boto3 import Session


class StateMachine:
    def __init__(self, arn: str, boto_session: Session):
        self.__arn = arn
        self.__sfn_client = boto_session.client('stepfunctions')

    def execute(self, execution_input):
        execution_arn = self.__start_execute(execution_input)
        final_state = self.__wait_execution(execution_arn)
        return final_state

    def __start_execute(self, input_data: dict) -> str:
        response = self.__sfn_client.start_execution(
            stateMachineArn=self.__arn,
            input=json.dumps(input_data),
            name=f"integ-test-{uuid4()}"
        )

        return response["executionArn"]

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
