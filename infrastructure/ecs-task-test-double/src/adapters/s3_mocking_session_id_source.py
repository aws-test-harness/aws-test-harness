import boto3


class S3MockingSessionIdSource:

    def __init__(self, test_context_bucket_name):
        super().__init__()
        self.__test_context_bucket_name = test_context_bucket_name

    def get_mocking_session_id(self):
        s3 = boto3.client('s3')
        get_object_response = s3.get_object(Bucket=self.__test_context_bucket_name,
                                            Key='test-id')
        mocking_session_id = get_object_response['Body'].read().decode('utf-8')
        return mocking_session_id
