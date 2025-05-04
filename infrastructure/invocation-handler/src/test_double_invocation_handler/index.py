import os
from typing import Dict, Any

import boto3

from test_double_invocation_handler.domain.invocation import Invocation
from test_double_invocation_handler.domain.invocation_result_service import InvocationResultService
from test_double_invocation_handler.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice

invocation_result_service = InvocationResultService(ServerlessInvocationPostOffice(
    os.environ['INVOCATION_QUEUE_URL'],
    os.environ['INVOCATION_TABLE_NAME'],
    boto3.Session()
))


def handler(event: Dict[str, Any], _: Any) -> Any:
    invocation = Invocation(
        id=event['invocationId'],
        target=event['invocationTarget'],
        payload=event
    )

    return invocation_result_service.generate_result_for(invocation)
