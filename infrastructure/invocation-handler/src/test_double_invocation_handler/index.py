import os
from time import sleep
from typing import Dict, Any

import boto3

from test_double_invocation_handler.domain.invocation_post_office import InvocationPostOffice
from test_double_invocation_handler.infrastructure.serverless_invocation_post_office import \
    ServerlessInvocationPostOffice

boto_session = boto3.Session()

invocation_post_office: InvocationPostOffice = ServerlessInvocationPostOffice(
    os.environ['INVOCATION_QUEUE_URL'],
    os.environ['INVOCATION_TABLE_NAME'],
    boto_session
)


def handler(event: Dict[str, Any], _: Any) -> Dict[str, Any]:
    invocation_target = event['invocationTarget']
    invocation_id = event['invocationId']

    # TODO: extract domain
    invocation_post_office.post_invocation(invocation_target, invocation_id, event)
    # TODO: Poll rather than sleep
    sleep(1)
    # TODO: Support result value of 'None'
    return invocation_post_office.maybe_collect_result(invocation_id)
