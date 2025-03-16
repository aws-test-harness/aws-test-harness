from typing import Callable, Optional

from mypy_boto3_sqs import SQSClient
from mypy_boto3_sqs.type_defs import MessageTypeDef

from infrastructure_test_support.eventual_consistency_utils import wait_for_value


def wait_for_sqs_message_matching(message_predicate: Callable[[MessageTypeDef], bool], invocation_queue_url: str,
                                  sqs_client: SQSClient) -> MessageTypeDef:
    def try_get_queue_message_satisfying_predicate() -> Optional[MessageTypeDef]:
        received_message_result = sqs_client.receive_message(
            QueueUrl=invocation_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=1,
            MessageAttributeNames=['All']
        )

        if 'Messages' in received_message_result:
            message = received_message_result['Messages'][0]
            sqs_client.delete_message(QueueUrl=invocation_queue_url, ReceiptHandle=message['ReceiptHandle'])

            if message_predicate(message):
                return message

        return None

    return wait_for_value(
        try_get_queue_message_satisfying_predicate,
        'SQS queue message that satisfies specified predicate'
    )
