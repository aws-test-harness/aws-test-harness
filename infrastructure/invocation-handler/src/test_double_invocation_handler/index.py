import os
from typing import Dict, Any

import boto3

from test_double_invocation_handler.domain.invocation_post_office import InvocationPostOffice
from test_double_invocation_handler.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice

boto_session = boto3.Session()

invocation_post_office: InvocationPostOffice = ServerlessInvocationPostOffice(
    os.environ['INVOCATION_QUEUE_URL'],
    boto_session
)


def handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    invocation_target = event['invocationTarget']
    invocation_id = event['invocationId']

    invocation_post_office.post_invocation(invocation_target, invocation_id, event)

    return dict()
