import os
from typing import Dict, Any, Optional

import boto3
from aws_lambda_typing.context import Context

from test_double_invocation_handler_messaging.domain.invocation import Invocation
from test_double_invocation_handler_function_code.domain.invocation_result_service import InvocationResultService
from test_double_invocation_handler_messaging.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice

TIMEOUT_BUFFER_MILLIS = 1000

invocation_result_service: Optional[InvocationResultService] = None


def get_invocation_result_service(context: Context) -> InvocationResultService:
    global invocation_result_service

    if invocation_result_service is None:
        timeout_millis = max(0, context.get_remaining_time_in_millis() - TIMEOUT_BUFFER_MILLIS)

        invocation_result_service = InvocationResultService(
            ServerlessInvocationPostOffice(
                os.environ['INVOCATION_QUEUE_URL'],
                os.environ['INVOCATION_TABLE_NAME'],
                boto3.Session()
            ),
            timeout_millis
        )

    return invocation_result_service


def handler(event: Dict[str, Any], context: Context) -> Any:
    result_service = get_invocation_result_service(context)

    invocation = Invocation(
        id=event['invocationId'],
        target=event['invocationTarget'],
        parameters=event['invocationParameters']
    )

    invocation_result_value = result_service.generate_result_for(invocation)

    return dict(invocationResult=invocation_result_value)
