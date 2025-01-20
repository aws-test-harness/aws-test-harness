from boto3 import Session


class CloudFormationResourceRegistry:
    def __init__(self, boto_session: Session):
        self.__cloudformation_client = boto_session.client('cloudformation')

    def get_physical_resource_id(self, cloudformation_stack_name, logical_resource_id):
        describe_stack_resource_result = self.__cloudformation_client.describe_stack_resource(
            StackName=cloudformation_stack_name,
            LogicalResourceId=logical_resource_id
        )

        return describe_stack_resource_result['StackResourceDetail']['PhysicalResourceId']
