from logging import Logger

from boto3 import Session

from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry
from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.state_machine import StateMachine
from aws_test_harness.infrastructure.boto_s3_bucket import BotoS3Bucket
from aws_test_harness.infrastructure.boto_state_machine import BotoStateMachine


class BotoAwsResourceFactory(AwsResourceFactory):
    def __init__(self, boto_session: Session, aws_resource_registry: AwsResourceRegistry, logger: Logger):
        self.__boto_session = boto_session
        self.__aws_resource_registry = aws_resource_registry
        self.__logger = logger

    def get_s3_bucket(self, resource_id: str) -> S3Bucket:
        bucket_arn = self.__aws_resource_registry.get_resource_arn(resource_id)
        bucket_name = bucket_arn.split('arn:aws:s3:::')[1]

        return BotoS3Bucket(bucket_name, self.__boto_session)

    # TODO: Retrofit tests
    def get_state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        state_machine_arn = self.__aws_resource_registry.get_resource_arn(cfn_logical_resource_id)
        return BotoStateMachine(state_machine_arn, self.__boto_session, self.__logger)
