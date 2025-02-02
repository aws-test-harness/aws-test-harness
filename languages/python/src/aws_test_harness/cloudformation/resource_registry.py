from boto3 import Session
from mypy_boto3_cloudformation.service_resource import CloudFormationServiceResource


class ResourceRegistry:
    def __init__(self, stack_name: str, boto_session: Session):
        self.__stack_name = stack_name
        self.__boto_resource: CloudFormationServiceResource = boto_session.resource('cloudformation')

    def get_physical_resource_id(self, logical_resource_id: str) -> str:
        stack_resource = self.__boto_resource.StackResource(self.__stack_name, logical_resource_id)
        return stack_resource.physical_resource_id
