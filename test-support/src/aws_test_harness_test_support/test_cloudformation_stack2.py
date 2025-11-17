from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


class TestCloudFormationStack2:
    __test__ = False

    __stack: TestCloudFormationStack

    def __init__(self, stack: TestCloudFormationStack):
        super().__init__()
        self.__stack = stack

    def has_s3_bucket_resource(self, resource_logical_id: str) -> bool:
        return self.__has_resource(resource_logical_id, 'AWS::S3::Bucket')

    def has_state_machine_resource(self, resource_logical_id: str) -> bool:
        return self.__has_resource(resource_logical_id, 'AWS::StepFunctions::StateMachine')

    def physical_id_for(self, resource_logical_id: str) -> str:
        return self.__stack.get_stack_resource_physical_id(resource_logical_id)

    def __has_resource(self, resource_logical_id: str, expected_resource_type: str) -> bool:
        resource = self.__stack.get_stack_resource(resource_logical_id)
        return resource and resource['ResourceType'] == expected_resource_type
