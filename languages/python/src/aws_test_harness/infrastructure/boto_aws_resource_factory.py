from boto3 import Session

from aws_test_harness.cloudformation.cloudformation_resource_registry import CloudFormationResourceRegistry
from aws_test_harness.domain.aws_resource_factory import AwsResourceFactory
from aws_test_harness.infrastructure.boto_s3_bucket import BotoS3Bucket


class BotoAwsResourceFactory(AwsResourceFactory):
    def __init__(self, boto_session: Session, cloudformation_resource_registry: CloudFormationResourceRegistry):
        self.__boto_session = boto_session
        self.__cloudformation_resource_registry = cloudformation_resource_registry

    def get_s3_bucket(self, cfn_logical_id: str) -> BotoS3Bucket:
        return BotoS3Bucket(
            self.__cloudformation_resource_registry.get_physical_resource_id(cfn_logical_id),
            self.__boto_session
        )
