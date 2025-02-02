import json
from logging import Logger
from typing import Dict, Any, Union, List, Optional, Sequence, Unpack

import yaml
from boto3 import Session
from botocore.exceptions import ClientError
from mypy_boto3_cloudformation.client import CloudFormationClient
from mypy_boto3_cloudformation.type_defs import ParameterTypeDef, CreateStackInputRequestTypeDef, \
    UpdateStackInputRequestTypeDef
from yaml import Loader


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

        stack_template_data = self.__create_stack_template_data(AWSTemplateFormatVersion, Transform, Resources, Outputs)
        self.__create_or_update_stack(stack_template_data)

    def ensure_state_matches_yaml_template_file(self, template_file_path: str, **parameters: str) -> None:
        self.__create_or_update_stack(yaml.load(open(template_file_path, 'r'), Loader=Loader), parameters)

    def __create_or_update_stack(self, stack_template_data, parameters: Dict[str, str] = None) -> None:
        self.__logger.info(f'Ensuring CloudFormation stack "{self.__stack_name}" is up-to-date...')

        common_upsert_kwargs = dict(
            StackName=self.__stack_name,
            TemplateBody=json.dumps(stack_template_data, default=str),
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            Parameters=[dict(ParameterKey=key, ParameterValue=value) for key, value in (parameters or {}).items()]
        )

        try:
            self.__create_stack(**common_upsert_kwargs)
        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            if client_error.response['Error']['Code'] != 'AlreadyExistsException':
                raise client_error

            self.__update_stack(**common_upsert_kwargs)
        self.__logger.info('CloudFormation stack is up-to-date.')

    def __create_stack(self, **common_upsert_kwargs: Unpack[CreateStackInputRequestTypeDef]) -> None:
        self.__cloudformation_client.create_stack(OnFailure='DELETE', **common_upsert_kwargs)
        create_stack_waiter = self.__cloudformation_client.get_waiter('stack_create_complete')
        create_stack_waiter.wait(StackName=self.__stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30))

    def __update_stack(self, **common_upsert_kwargs: Unpack[UpdateStackInputRequestTypeDef]) -> None:
        try:
            self.__cloudformation_client.update_stack(**common_upsert_kwargs)
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
