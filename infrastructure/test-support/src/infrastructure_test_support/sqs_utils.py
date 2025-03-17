from typing import Callable, Optional

from mypy_boto3_sqs import SQSClient
from mypy_boto3_sqs.type_defs import MessageTypeDef

from infrastructure_test_support.eventual_consistency_utils import wait_for_value_matching


def wait_for_sqs_message_matching(message_predicate: Callable[[MessageTypeDef], bool], queue_url: str,
                                  sqs_client: SQSClient) -> MessageTypeDef:
    def try_get_queue_message() -> Optional[MessageTypeDef]:
        received_message_result = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=1,
            MessageAttributeNames=['All']
        )

        if 'Messages' in received_message_result:
            message = received_message_result['Messages'][0]
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])
            return message

        return None

    return wait_for_value_matching(
        try_get_queue_message,
        'SQS queue message that satisfies specified predicate',
        message_predicate
    )
