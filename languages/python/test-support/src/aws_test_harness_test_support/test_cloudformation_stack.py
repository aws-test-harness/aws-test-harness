from typing import Dict, Any, Union, List, Optional

from aws_test_harness_test_support.cloudformation_driver import CloudFormationDriver


class TestCloudFormationStack:
    def __init__(self, stack_name: str, cloudformation_driver: CloudFormationDriver):
        self.__stack_name = stack_name
        self.__cloudformation_driver = cloudformation_driver

    def get_output_value(self, output_name: str) -> Optional[str]:
        return self.__cloudformation_driver.get_stack_output_value(self.__stack_name,
                                                                   output_name)

    # noinspection PyPep8Naming
    def ensure_state_is(self, Resources: Dict[str, Any],
                        AWSTemplateFormatVersion: str = '2010-09-09',
                        Transform: Optional[Union[str, List[str]]] = None,
                        Outputs: Optional[Dict[str, Any]] = None) -> None:
        stack_template_data = dict(
            AWSTemplateFormatVersion=AWSTemplateFormatVersion,
            Resources=Resources,
        )

        if Transform:
            stack_template_data['Transform'] = Transform

        if Outputs:
            stack_template_data['Outputs'] = Outputs

        self.__cloudformation_driver.ensure_stack_is_up_to_date(
            self.__stack_name,
            stack_template_data
        )
