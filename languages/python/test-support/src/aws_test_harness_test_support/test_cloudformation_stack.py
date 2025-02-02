import json
from logging import Logger
from typing import Dict, Any, Union, List, Optional

from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_cloudformation.client import CloudFormationClient


class TestCloudFormationStack:
    def __init__(self, stack_name: str, logger: Logger, boto_session: Session):
        self.__stack_name = stack_name
        self.__logger = logger
        self.__cloudformation_client: CloudFormationClient = boto_session.client('cloudformation')

    def get_output_value(self, output_name: str) -> str:
        result = self.__cloudformation_client.describe_stacks(StackName=self.__stack_name)

        output_values = [
            output['OutputValue']
            for output in result['Stacks'][0]['Outputs'] if
            output['OutputKey'] == output_name
        ]

        if len(output_values) == 0:
            raise Exception(f'Output "{output_name}" not found in stack "{self.__stack_name}"')

        return output_values[0]

    # noinspection PyPep8Naming
    def ensure_state_is(self, Resources: Dict[str, Any],
                        AWSTemplateFormatVersion: str = '2010-09-09',
                        Transform: Optional[Union[str, List[str]]] = None,
                        Outputs: Optional[Dict[str, Any]] = None) -> None:

        self.__logger.info(f'Ensuring CloudFormation stack "{self.__stack_name}" is up-to-date...')

        stack_template_data = self.__create_stack_template_data(AWSTemplateFormatVersion, Transform, Resources, Outputs)

        try:
            self.__create_stack(stack_template_data)
        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            if client_error.response['Error']['Code'] != 'AlreadyExistsException':
                raise client_error

            self.__update_stack(stack_template_data)

        self.__logger.info('CloudFormation stack is up-to-date.')

    def __create_stack(self, stack_template_data: Dict[str, Any]) -> None:
        self.__cloudformation_client.create_stack(
            StackName=self.__stack_name,
            TemplateBody=json.dumps(stack_template_data),
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            OnFailure='DELETE'
        )
        create_stack_waiter = self.__cloudformation_client.get_waiter('stack_create_complete')
        create_stack_waiter.wait(StackName=self.__stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30))

    def __update_stack(self, stack_template_data: Dict[str, Any]) -> None:
        try:
            self.__cloudformation_client.update_stack(
                StackName=self.__stack_name,
                TemplateBody=json.dumps(stack_template_data),
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            )
            update_stack_waiter = self.__cloudformation_client.get_waiter('stack_update_complete')
            update_stack_waiter.wait(StackName=self.__stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30))
        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            error = client_error.response['Error']
            if not (error['Code'] == 'ValidationError' and error['Message'] == 'No updates are to be performed.'):
                raise client_error

    # noinspection PyPep8Naming
    @staticmethod
    def __create_stack_template_data(AWSTemplateFormatVersion: str, Transform: Optional[Union[str, List[str]]],
                                     Resources: Dict[str, Any], Outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        stack_template_data = dict(
            AWSTemplateFormatVersion=AWSTemplateFormatVersion,
            Resources=Resources,
        )

        if Transform:
            stack_template_data['Transform'] = Transform

        if Outputs:
            stack_template_data['Outputs'] = Outputs

        return stack_template_data
