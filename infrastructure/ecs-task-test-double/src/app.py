import os
import sys

from adapters.dynamodb_results_inbox import DynamoDBResultsInbox
from adapters.s3_mocking_session_id_source import S3MockingSessionIdSource
from adapters.sqs_invocation_handling_queue import SQSInvocationHandlingQueue
from adapters.system_clock_poller import SystemClockPoller
from domain.async_invocation_handler import AsyncInvocationHandler
from adapters.http_ecs_metadata_source import HttpECSMetadataSource
from json_logger import JSONLogger


def main():
    logger = JSONLogger()
    logger.info("ECS Task Runner starting")

    async_invocation_handler = AsyncInvocationHandler(
        HttpECSMetadataSource(os.environ['ECS_CONTAINER_METADATA_URI_V4']),
        S3MockingSessionIdSource(os.environ['__AWS_TEST_HARNESS__TEST_CONTEXT_BUCKET_NAME']),
        SQSInvocationHandlingQueue(os.environ['__AWS_TEST_HARNESS__EVENTS_QUEUE_URL'], logger),
        DynamoDBResultsInbox(os.environ['__AWS_TEST_HARNESS__RESULTS_TABLE_NAME'], logger),
        SystemClockPoller(logger),
        logger
    )

    exit_code = async_invocation_handler.handle_invocation()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
