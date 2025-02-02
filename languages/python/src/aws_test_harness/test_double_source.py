from typing import Callable, Optional

from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry
from aws_test_harness.s3.s3_bucket import S3Bucket


class TestDoubleSource:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, create_test_double_resource_registry: Callable[[], ResourceRegistry], boto_session: Session):
        self.__create_test_double_resource_registry = create_test_double_resource_registry
        self.__boto_session = boto_session
        self.__test_double_resource_registry: Optional[ResourceRegistry] = None

    def s3_bucket(self, test_double_name: str) -> S3Bucket:
        bucket_name = self.__get_test_double_physical_id(test_double_name)
        return S3Bucket(bucket_name, self.__boto_session)

    def __get_test_double_physical_id(self, test_double_name: str) -> str:
        if self.__test_double_resource_registry is None:
            self.__test_double_resource_registry = self.__create_test_double_resource_registry()

        return self.__test_double_resource_registry.get_physical_resource_id(f'{test_double_name}S3Bucket')
