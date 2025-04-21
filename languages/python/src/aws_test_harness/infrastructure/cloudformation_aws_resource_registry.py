from boto3 import Session
from mypy_boto3_cloudformation.service_resource import CloudFormationServiceResource

from aws_test_harness.domain.aws_resource_registry import AwsResourceRegistry


class CloudFormationAwsResourceRegistry(AwsResourceRegistry):
    def __init__(self, stack_name: str, boto_session: Session):
        self.__stack_name = stack_name
        self.__boto_resource: CloudFormationServiceResource = boto_session.resource('cloudformation')

    def get_resource_arn(self, resource_id: str) -> str:
        stack_resource = self.__boto_resource.StackResource(self.__stack_name, resource_id)

        if stack_resource.resource_type == 'AWS::S3::Bucket':
            return f'arn:aws:s3:::{stack_resource.physical_resource_id}'

        return stack_resource.physical_resource_id
