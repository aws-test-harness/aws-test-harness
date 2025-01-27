from boto3 import Session
from mypy_boto3_cloudformation.client import CloudFormationClient


class ResourceRegistry:
    def __init__(self, boto_session: Session):
        self.__cloudformation_client: CloudFormationClient = boto_session.client('cloudformation')

    def get_physical_resource_id(self, logical_resource_id: str, cloudformation_stack_name: str) -> str:
        describe_stack_resource_result = self.__cloudformation_client.describe_stack_resource(
            StackName=cloudformation_stack_name,
            LogicalResourceId=logical_resource_id
        )

        return describe_stack_resource_result['StackResourceDetail']['PhysicalResourceId']
