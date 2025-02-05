import json
from datetime import datetime
from enum import StrEnum
from time import sleep
from typing import Optional

from mypy_boto3_stepfunctions import SFNClient


class StateMachineExecutionState(StrEnum):
    RUNNING = "RUNNING"
    ABORTED = "ABORTED"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


FINAL_STATES = [
    StateMachineExecutionState.SUCCEEDED,
    StateMachineExecutionState.FAILED,
    StateMachineExecutionState.TIMED_OUT,
    StateMachineExecutionState.ABORTED
]


class StateMachineExecution:
    __status: Optional[StateMachineExecutionState]
    __output: Optional[str]
    __cause: Optional[str]
    __error: Optional[str]

    def __init__(self, execution_arn: str, sfn_client: SFNClient):
        self.__execution_arn = execution_arn
        self.__sfn_client = sfn_client
        self.__status = None

    def assert_succeeded(self):
        assert self.succeeded, (
            f"Execution failed with error '{self.failure_error}' and cause: '{self.failure_cause}'."
            if self.failed else f"Execution did not succeed. Current status is '{self.status}'."
        )

    @property
    def name(self):
        return self.__sfn_client.describe_execution(executionArn=self.__execution_arn)["name"]

    @property
    def running(self):
        return self.status == StateMachineExecutionState.RUNNING

    @property
    def succeeded(self):
        return self.status == StateMachineExecutionState.SUCCEEDED

    @property
    def failed(self):
        return self.status == StateMachineExecutionState.FAILED

    @property
    def timed_out(self):
        return self.status == StateMachineExecutionState.TIMED_OUT

    @property
    def aborted(self):
        return self.status == StateMachineExecutionState.ABORTED

    @property
    def status(self):
        if self.__status not in FINAL_STATES:
            self.__retrieve_status()

        return self.__status

    @property
    def output_json(self):
        return json.loads(self.output)

    @property
    def output(self):
        if self.__status != StateMachineExecutionState.SUCCEEDED:
            raise Exception(
                f"State machine output unavailable because execution is currently in a '{self.__status}' state")

        return self.__output

    @property
    def failure_cause(self):
        if self.__status != StateMachineExecutionState.FAILED:
            raise Exception(
                f"State machine failure cause is unavailable because execution is currently in a '{self.__status}' state")

        return self.__cause

    @property
    def failure_error(self):
        if self.__status != StateMachineExecutionState.FAILED:
            raise Exception(
                f"State machine failure error is unavailable because execution is currently in a '{self.__status}' state")

        return self.__error

    def wait_for_completion(self, timeout_seconds: float = 30):
        start_time = datetime.now()

        while self.status == StateMachineExecutionState.RUNNING:
            wait_time = datetime.now() - start_time

            if wait_time.total_seconds() >= timeout_seconds:
                raise Exception(f"State machine execution timed out after {timeout_seconds} seconds")

            sleep(0.5)

    def __retrieve_status(self):
        response = self.__sfn_client.describe_execution(executionArn=self.__execution_arn)

        self.__status = StateMachineExecutionState(response["status"])

        if self.__status == StateMachineExecutionState.SUCCEEDED:
            self.__output = response.get("output")

        if self.__status == StateMachineExecutionState.FAILED:
            self.__cause = response.get("cause")
            self.__error = response.get("error")
