import json
from datetime import datetime
from logging import Logger
from typing import Dict, Any, Union, List, Optional, Unpack, cast, Callable

import yaml
from boto3 import Session
from botocore.exceptions import ClientError, WaiterError
from mypy_boto3_cloudformation.client import CloudFormationClient
from mypy_boto3_cloudformation.literals import OnFailureType
from mypy_boto3_cloudformation.type_defs import StackResourceDetailTypeDef, CreateStackInputTypeDef, \
    UpdateStackInputTypeDef


class TestCloudFormationStack:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, stack_name: str, logger: Logger, boto_session: Session):
        self.__stack_name = stack_name
        self.__logger = logger
        self.__cloudformation_client: CloudFormationClient = boto_session.client('cloudformation')

    @property
    def name(self) -> str:
        return self.__stack_name

    def get_stack_resource_physical_id(self, logical_id: str) -> str:
        resource = self.get_stack_resource(logical_id)
        assert resource is not None
        return resource['PhysicalResourceId']

    def get_stack_resource(self, logical_id: str) -> Optional[StackResourceDetailTypeDef]:
        try:
            result = self.__cloudformation_client.describe_stack_resource(
                StackName=self.__stack_name,
                LogicalResourceId=logical_id
            )

            return result['StackResourceDetail']
        except ClientError as client_error:
            error = client_error.response['Error']

            if error['Code'] == 'ValidationError' and 'does not exist' in error['Message']:
                return None

            raise client_error

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
                        Outputs: Optional[Dict[str, Any]] = None,
                        Parameters: Optional[Dict[str, Any]] = None,
                        **parameter_values: str) -> None:

        stack_template_data = self.__create_stack_template_data(
            AWSTemplateFormatVersion, Transform, Parameters, Resources, Outputs
        )

        self.__logger.info(
            f'Ensuring CloudFormation stack "{self.__stack_name}" matches state defined by the following template:'
            f'\n\n{yaml.dump(stack_template_data, sort_keys=False)}' +
            (
                '\nand the following template parameter values:\n\n' +
                '\n'.join(f'{name}: "{value}"' for name, value in parameter_values.items()) + '\n'
                if parameter_values else ''
            )
        )

        common_stack_operation_kwargs: Union[CreateStackInputTypeDef, UpdateStackInputTypeDef] = dict(
            StackName=self.__stack_name,
            TemplateBody=json.dumps(stack_template_data),
            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            Parameters=[dict(ParameterKey=key, ParameterValue=value) for key, value in (parameter_values or {}).items()]
        )

        self.__create_or_update_stack(common_stack_operation_kwargs)

        self.__logger.info('CloudFormation stack is up-to-date.')

    def __create_or_update_stack(self, common_stack_operation_kwargs: Union[
        CreateStackInputTypeDef, UpdateStackInputTypeDef]) -> None:
        try:
            self.__create_stack(**cast(CreateStackInputTypeDef, common_stack_operation_kwargs))
        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            if client_error.response['Error']['Code'] != 'AlreadyExistsException':
                raise client_error

            self.__update_stack(**cast(UpdateStackInputTypeDef, common_stack_operation_kwargs))

    def __create_stack(self, **common_upsert_kwargs: Unpack[CreateStackInputTypeDef]) -> None:
        common_upsert_kwargs['OnFailure'] = cast(OnFailureType, "DELETE")
        self.__cloudformation_client.create_stack(**common_upsert_kwargs)

        create_stack_waiter = self.__cloudformation_client.get_waiter('stack_create_complete')
        self.__with_stack_change_failure_reason_on_waiter_error(
            lambda: create_stack_waiter.wait(StackName=self.__stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30)),
            self.__stack_name,
            'create'
        )

    def __update_stack(self, **common_upsert_kwargs: Unpack[UpdateStackInputTypeDef]) -> None:
        try:
            self.__cloudformation_client.update_stack(**common_upsert_kwargs)
            update_stack_waiter = self.__cloudformation_client.get_waiter('stack_update_complete')
            self.__with_stack_change_failure_reason_on_waiter_error(
                lambda: update_stack_waiter.wait(
                    StackName=self.__stack_name,
                    WaiterConfig=dict(Delay=3, MaxAttempts=30)
                ),
                self.__stack_name,
                'update'
            )
        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            error = client_error.response['Error']
            if not (error['Code'] == 'ValidationError' and error['Message'] == 'No updates are to be performed.'):
                raise client_error

    # noinspection PyPep8Naming
    @staticmethod
    def __create_stack_template_data(AWSTemplateFormatVersion: str, Transform: Optional[Union[str, List[str]]],
                                     Parameters: Optional[Dict[str, Any]], Resources: Dict[str, Any],
                                     Outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        stack_template_data = cast(Dict[str, Any], dict(
            AWSTemplateFormatVersion=AWSTemplateFormatVersion,
            Resources=Resources,
        ))

        if Transform:
            stack_template_data['Transform'] = Transform

        if Parameters:
            stack_template_data['Parameters'] = Parameters

        if Outputs:
            stack_template_data['Outputs'] = Outputs

        return stack_template_data

    def __with_stack_change_failure_reason_on_waiter_error(self, wait: Callable[[], None], stack_name: str,
                                                           stack_change_type: str) -> None:
        try:
            wait()
        except WaiterError as waiter_error:
            describe_stacks_result = self.__cloudformation_client.describe_stacks(StackName=stack_name)
            stack_description = describe_stacks_result['Stacks'][0]
            stack_change_start_time = stack_description.get('LastUpdatedTime')

            likely_stack_change_failure_reason: Optional[str] = None

            if stack_change_start_time:
                likely_stack_change_failure_reason = self.__get_likely_stack_change_failure_reason(
                    stack_name, stack_change_start_time
                )

            exception_message = (
                    f'Exception thrown whilst waiting for stack to {stack_change_type}. ' +
                    (
                        f'The likely reason for the failure was: "{likely_stack_change_failure_reason}"'
                        if likely_stack_change_failure_reason
                        else 'Unable to determine the reason for the failure.'
                    )
            )

            raise Exception(exception_message) from waiter_error

    def __get_likely_stack_change_failure_reason(self, stack_name: str, stack_change_start_time: datetime) -> Optional[
        str]:
        describe_stack_events_paginator = self.__cloudformation_client.get_paginator('describe_stack_events')

        for page in describe_stack_events_paginator.paginate(StackName=stack_name):
            for event in page['StackEvents']:
                status_reason = event.get('ResourceStatusReason')

                if status_reason:
                    return status_reason

                if event['Timestamp'] < stack_change_start_time:
                    return None

        return None
