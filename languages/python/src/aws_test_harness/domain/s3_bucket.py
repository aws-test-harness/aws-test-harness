from abc import ABCMeta, abstractmethod
from typing import Unpack

from mypy_boto3_s3.type_defs import PutObjectRequestBucketPutObjectTypeDef


class S3Bucket(metaclass=ABCMeta):
    @abstractmethod
    def put_object(self, **put_object_kwargs: Unpack[PutObjectRequestBucketPutObjectTypeDef]) -> None:
        pass
