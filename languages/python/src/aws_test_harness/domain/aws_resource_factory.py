from abc import ABCMeta, abstractmethod

from aws_test_harness.domain.s3_bucket import S3Bucket


class AwsResourceFactory(metaclass=ABCMeta):
    @abstractmethod
    def get_s3_bucket(self, resource_id: str) -> S3Bucket:
        pass
