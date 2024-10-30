from boto3 import Session
from mypy_boto3_s3.service_resource import S3ServiceResource, Bucket


class S3Bucket:

    def __init__(self, name: str, session: Session):
        super().__init__()

        self.__name = name
        s3_resource: S3ServiceResource = session.resource('s3')
        self.__boto_bucket_resource: Bucket = s3_resource.Bucket(name)

    def put_object(self, key, content):
        self.__boto_bucket_resource.put_object(Key=key, Body=content)

    def get_object(self, key):
        return self.__boto_bucket_resource.Object(key).get()['Body'].read().decode('utf-8')
