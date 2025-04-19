from logging import Logger
from threading import Thread
from time import sleep
from typing import Callable

from boto3 import Session
from mypy_boto3_sqs import SQSServiceResource

from aws_test_harness.domain.invocation_listener import InvocationListener


class SqsMessageInvocationListener(InvocationListener):
    __listening = False
    __stopping = False

    def __init__(self, invocation_queue_url: str, boto_session: Session, logger: Logger):
        sqs_resource: SQSServiceResource = boto_session.resource('sqs')
        self.__invocation_queue = sqs_resource.Queue(invocation_queue_url)
        self.__logger = logger

    def listen(self, handle_invocation: Callable[[str, str], None]) -> None:
        if self.__listening:
            return

        self.__listening = True

        def listen_for_invocation_messages() -> None:
            while not self.__stopping:
                try:
                    messages = self.__invocation_queue.receive_messages(
                        MessageAttributeNames=['All'],
                        MaxNumberOfMessages=1
                    )

                    if messages:
                        message = messages[0]
                        # message.delete()

                        handle_invocation(
                            message.message_attributes['InvocationTarget']['StringValue'],
                            message.message_attributes['InvocationId']['StringValue']
                        )

                except BaseException as e:
                    self.__logger.exception('Uncaught exception in invocation listener thread', exc_info=e)

            self.__stopping = False
            self.__listening = False

        thread = Thread(target=listen_for_invocation_messages, daemon=True)
        thread.start()

    def stop(self):
        self.__stopping = True

        def wait_to_stop_listening():
            while self.__listening:
                sleep(0.01)

        thread = Thread(target=wait_to_stop_listening, daemon=True)
        thread.start()
        thread.join()
