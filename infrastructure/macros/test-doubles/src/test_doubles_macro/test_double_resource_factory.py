from typing import Dict, Any, List

from test_doubles_macro.test_double_invocation_handling_resource_factory import \
    TestDoubleInvocationHandlingResourceFactory
from test_doubles_macro.test_double_s3_bucket_resource_factory import TestDoubleS3BucketResourceFactory
from test_doubles_macro.test_double_state_machine_resource_factory import TestDoubleStateMachineResourceFactory


class TestDoubleResourceFactory:
    @classmethod
    def generate_additional_resources(cls, desired_test_doubles: Dict[str, List[str]]) -> Dict[str, Any]:
        additional_resources: Dict[str, Dict[str, Any]] = {}

        for s3_bucket_id in cls.__try_get_string_list('AWSTestHarnessS3Buckets', desired_test_doubles):
            TestDoubleResourceFactory.__add_s3_bucket_resources_for(s3_bucket_id, additional_resources)

        test_double_invocation_handler_function_logical_id = 'AWSTestHarnessTestDoubleInvocationHandlerFunction'

        state_machine_ids = cls.__try_get_string_list('AWSTestHarnessStateMachines', desired_test_doubles)

        if state_machine_ids:
            cls.__add_test_double_invocation_handling_resources_for(
                test_double_invocation_handler_function_logical_id, additional_resources
            )

        for state_machine_id in state_machine_ids:
            cls.__add_state_machine_resources_for(
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

    @classmethod
    def __add_test_double_invocation_handling_resources_for(cls, function_logical_id: str, additional_resources: Dict[str, Dict[str, Any]]) -> None:
        function_role_logical_id = 'AWSTestHarnessTestDoubleInvocationHandlerFunctionRole'
        queue_logical_id = 'AWSTestHarnessTestDoubleInvocationQueue'

        resource_descriptions = TestDoubleInvocationHandlingResourceFactory.generate_resources(
            function_role_logical_id,
            queue_logical_id
        )

        additional_resources[queue_logical_id] = resource_descriptions.invocation_queue
        additional_resources[function_role_logical_id] = resource_descriptions.invocation_handler_function_role
        additional_resources[function_logical_id] = resource_descriptions.invocation_handler_function

    @staticmethod
    def __try_get_string_list(key: str, dictionary: Dict[str, List[str]]) -> List[str]:
        return dictionary.get(key, [])
