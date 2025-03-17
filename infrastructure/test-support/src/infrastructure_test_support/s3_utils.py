import os

from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client


def sync_file_to_s3(file_path: str, bucket_name: str, key: str, s3_client: S3Client) -> None:
    if is_s3_key_stale(bucket_name, key, file_path, s3_client):
        s3_client.upload_file(Filename=file_path, Bucket=bucket_name, Key=key)


# Like the AWS CLI 's3 sync' command, use file size and timestamp to determine staleness.
# ETags can't be used because the SDK uses multi-part uploads which generate a composite ETag.
def is_s3_key_stale(bucket_name: str, s3_key: str, local_file_path: str, s3_client: S3Client) -> bool:
    try:
        head_object_result = s3_client.head_object(
            Bucket=bucket_name,
            Key=s3_key
        )
    except ClientError as client_error:
        error = client_error.response['Error']

        if error['Code'] == '404':
            return True

        raise client_error

    if os.path.getsize(local_file_path) != head_object_result['ContentLength']:
        return True

    if os.path.getmtime(local_file_path) > head_object_result['LastModified'].timestamp():
        return True

    return False
