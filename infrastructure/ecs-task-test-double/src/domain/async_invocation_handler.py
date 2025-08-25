import os
import sys
from uuid import uuid4

from domain.invocation import Invocation
from domain.task_context import TaskContext


class AsyncInvocationHandler:
    def __init__(self, ecs_metadata_source, mocking_session_id_source, invocation_handling_queue, result_inbox, poller,
                 logger):
        super().__init__()
        self.__result_inbox = result_inbox
        self.__poller = poller
        self.__mocking_session_id_source = mocking_session_id_source
        self.__logger = logger
        self.__invocation_handling_queue = invocation_handling_queue
        self.__ecs_metadata_source = ecs_metadata_source

    def handle_invocation(self):
        invocation_id = str(uuid4())
        task_metadata = self.__ecs_metadata_source.fetch_task_metadata()
        mocking_session_id = self.__mocking_session_id_source.get_mocking_session_id()

        task_definition_arn = task_metadata['taskDefinition']['arn']

        self.__logger.set_context(
            task_definition_arn=task_definition_arn,
            invocation_id=invocation_id,
            mocking_session_id=mocking_session_id
        )

        container_name = task_metadata['containerName']

        invocation = Invocation(
            task_definition_arn=task_definition_arn,
            task_family=task_metadata['taskDefinition']['family'],
            container_name=container_name,
            id=invocation_id,
            task_context=TaskContext(command_args=sys.argv[1:], environment_variables=dict(os.environ)),
            mocking_session_id=mocking_session_id
        )

        self.__invocation_handling_queue.schedule_handling(invocation)

        try:
            exit_code = self.__poller.poll_for_value(
                lambda: self.__result_inbox.try_get_exit_code_for(task_definition_arn, container_name, invocation_id),
                timeout_seconds=10,
                interval_seconds=0.2
            )

            if exit_code == 0:
                self.__logger.info("ECS Task Runner completed successfully")
            else:
                self.__logger.error("ECS Task Runner failed", exitCode=exit_code)

            return exit_code
        except TimeoutError:
            self.__logger.error("Timeout: No result found", timeoutSeconds=10)
            return 1
