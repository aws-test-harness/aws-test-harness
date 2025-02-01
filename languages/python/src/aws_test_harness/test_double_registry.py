from boto3 import Session

from aws_test_harness.cloudformation.resource_registry import ResourceRegistry


# TODO: Retrofit test coverage
class TestDoubleRegistry:
    def __init__(self, cfn_stack_name: str, aws_profile: str) -> None:
        boto_session = Session(profile_name=aws_profile)
        resource_registry = ResourceRegistry(cfn_stack_name, boto_session)
        test_doubles_stack_name = resource_registry.get_physical_resource_id('TestDoubles')
        self.__test_doubles_stack_resource_registry = ResourceRegistry(test_doubles_stack_name, boto_session)

    def get_s3_bucket_name(self, test_double_name: str) -> str:
        return self.__test_doubles_stack_resource_registry.get_physical_resource_id(f'{test_double_name}Bucket')
