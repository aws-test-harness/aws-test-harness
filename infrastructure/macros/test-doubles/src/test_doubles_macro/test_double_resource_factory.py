from typing import Dict, Any, List

from test_doubles_macro.test_double_invocation_handling_resource_factory import \
    TestDoubleInvocationHandlingResourceFactory
from test_doubles_macro.test_double_s3_bucket_resource_factory import TestDoubleS3BucketResourceFactory
from test_doubles_macro.test_double_state_machine_resource_factory import TestDoubleStateMachineResourceFactory


class TestDoubleResourceFactory:
    def __init__(self, invocation_handler_function_code_s3_bucket: str, invocation_handler_function_code_s3_key: str):
        self.__invocation_handling_resource_factory = TestDoubleInvocationHandlingResourceFactory(
            invocation_handler_function_code_s3_bucket,
            invocation_handler_function_code_s3_key)

    def generate_additional_resources(self, desired_test_doubles: Dict[str, List[str]]) -> Dict[str, Any]:
        additional_resources: Dict[str, Dict[str, Any]] = {}

        for s3_bucket_id in self.__try_get_string_list('AWSTestHarnessS3Buckets', desired_test_doubles):
            TestDoubleResourceFactory.__add_s3_bucket_resources_for(s3_bucket_id, additional_resources)

        test_double_invocation_handler_function_logical_id = 'AWSTestHarnessTestDoubleInvocationHandlerFunction'

        state_machine_ids = self.__try_get_string_list('AWSTestHarnessStateMachines', desired_test_doubles)

        if state_machine_ids:
            self.__add_test_double_invocation_handling_resources_for(
                test_double_invocation_handler_function_logical_id, additional_resources
            )

        for state_machine_id in state_machine_ids:
            self.__add_state_machine_resources_for(
                state_machine_id, test_double_invocation_handler_function_logical_id, additional_resources
            )

        return additional_resources

    @staticmethod
    def __add_s3_bucket_resources_for(s3_bucket_id: str, additional_resources: Dict[str, Dict[str, Any]]) -> None:
        additional_resources[f'{s3_bucket_id}AWSTestHarnessS3Bucket'] = \
            TestDoubleS3BucketResourceFactory.generate_resource()

    @staticmethod
    def __add_state_machine_resources_for(state_machine_id: str,
                                          test_double_invocation_handler_function_logical_id: str,
                                          additional_resources: Dict[str, Dict[str, Any]]) -> None:
        state_machine_role_logical_id = 'AWSTestHarnessStateMachineRole'

        resource_descriptions = TestDoubleStateMachineResourceFactory.generate_resources(
            state_machine_role_logical_id,
            test_double_invocation_handler_function_logical_id
        )

        additional_resources[state_machine_role_logical_id] = resource_descriptions.role
        additional_resources[f'{state_machine_id}AWSTestHarnessStateMachine'] = resource_descriptions.state_machine

    def __add_test_double_invocation_handling_resources_for(self, function_logical_id: str,
                                                            additional_resources: Dict[str, Dict[str, Any]]) -> None:
        function_role_logical_id = 'AWSTestHarnessTestDoubleInvocationHandlerFunctionRole'
        queue_logical_id = 'AWSTestHarnessTestDoubleInvocationQueue'
        invocation_table_logical_id = 'AWSTestHarnessTestDoubleInvocationTable'

        resource_descriptions = self.__invocation_handling_resource_factory.generate_resources(
            function_role_logical_id, queue_logical_id, invocation_table_logical_id
        )

        additional_resources[queue_logical_id] = resource_descriptions.invocation_queue
        additional_resources[invocation_table_logical_id] = resource_descriptions.invocation_table
        additional_resources[function_role_logical_id] = resource_descriptions.invocation_handler_function_role
        additional_resources[function_logical_id] = resource_descriptions.invocation_handler_function

    @staticmethod
    def __try_get_string_list(key: str, dictionary: Dict[str, List[str]]) -> List[str]:
        return dictionary.get(key, [])
