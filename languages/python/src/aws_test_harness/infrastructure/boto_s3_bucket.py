from typing import Unpack

from boto3 import Session
from mypy_boto3_s3 import S3ServiceResource
from mypy_boto3_s3.type_defs import PutObjectRequestBucketPutObjectTypeDef

from aws_test_harness.s3.s3_bucket import S3Bucket


class BotoS3Bucket(S3Bucket):
    def __init__(self, bucket_name: str, boto_session: Session):
        s3_resource: S3ServiceResource = boto_session.resource('s3')
        self.__s3_bucket = s3_resource.Bucket(bucket_name)

    def put_object(self, **put_object_kwargs: Unpack[PutObjectRequestBucketPutObjectTypeDef]) -> None:
        self.__s3_bucket.put_object(**put_object_kwargs)
