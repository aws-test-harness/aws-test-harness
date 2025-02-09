from boto3 import Session
from mypy_boto3_s3 import S3Client


class S3TestClient:
    def __init__(self, boto_session: Session):
        self.__s3_client: S3Client = boto_session.client('s3')

    def get_object_content(self, bucket_name: str, object_key: str) -> str:
        result = self.__s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return result['Body'].read().decode('utf-8')
