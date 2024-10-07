from functools import reduce

from boto3 import Session


class CloudFormationStack:

    def __init__(self, cloudformation_stack_name: str, boto_session: Session):
        super().__init__()
        self.__cloudformation_stack_name = cloudformation_stack_name
        self.__boto_session = boto_session

    def get_physical_resource_id_for(self, fully_qualified_logical_resource_id: str):
        logical_resource_parts = fully_qualified_logical_resource_id.split('::')

        def reducer(parent_id: str, logical_resource_id: str):
            return self.__get_physical_resource_id_in_stack(parent_id, logical_resource_id)

        return reduce(reducer, logical_resource_parts, self.__cloudformation_stack_name)

    def __get_physical_resource_id_in_stack(self, stack_name: str, logical_resource_id: str):
        client = self.__boto_session.client("cloudformation")
        response = client.list_stack_resources(StackName=stack_name)
        resources = response["StackResourceSummaries"]
        matching_resources = [
            resource for resource in resources if resource["LogicalResourceId"] == logical_resource_id
        ]

        if not matching_resources:
            raise Exception(f"Cannot find {logical_resource_id}")

        return matching_resources[0]["PhysicalResourceId"]
