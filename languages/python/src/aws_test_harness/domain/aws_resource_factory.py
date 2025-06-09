from abc import ABCMeta, abstractmethod

from aws_test_harness.domain.s3_bucket import S3Bucket
from aws_test_harness.domain.state_machine import StateMachine


class AwsResourceFactory(metaclass=ABCMeta):
    @abstractmethod
    def get_s3_bucket(self, resource_id: str) -> S3Bucket:
        pass

    @abstractmethod
    def get_state_machine(self, cfn_logical_resource_id: str) -> StateMachine:
        pass
