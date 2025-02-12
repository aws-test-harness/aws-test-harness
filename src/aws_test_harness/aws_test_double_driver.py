from boto3 import Session

from aws_test_harness.cloudformation_stack import CloudFormationStack
from aws_test_harness.dynamodb_table import DynamoDBTable
from aws_test_harness.s3_bucket import S3Bucket


class AWSTestDoubleDriver:
    __test_context_bucket: S3Bucket = None
    __events_queue_url: str = None
    __results_table_name: str = None

    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session: Session):
        self.__cloudformation_stack = cloudformation_stack
        self.__boto_session = boto_session

    def get_s3_bucket(self, bucket_id) -> S3Bucket:
        s3_bucket_name = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{bucket_id}Bucket'
        )

        return S3Bucket(s3_bucket_name, self.__boto_session)

    def get_dynamodb_table(self, table_name) -> DynamoDBTable:
        ddb_table_name = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{table_name}Table'
        )

        return DynamoDBTable(ddb_table_name, self.__boto_session)

    def get_lambda_function_name(self, function_id):
        return self.__cloudformation_stack.get_physical_resource_id_for(f'{function_id}Function')

    @property
    def events_queue_url(self) -> str:
        if self.__events_queue_url is None:
            self.__events_queue_url = self.__cloudformation_stack.get_physical_resource_id_for('EventsQueue')

        return self.__events_queue_url

    @property
    def results_table_name(self) -> str:
        if self.__results_table_name is None:
            self.__results_table_name = self.__cloudformation_stack.get_physical_resource_id_for('ResultsTable')

        return self.__results_table_name

    @property
    def test_context_bucket(self) -> S3Bucket:
        if self.__test_context_bucket is None:
            self.__test_context_bucket = self.get_s3_bucket('TestContext')

        return self.__test_context_bucket
