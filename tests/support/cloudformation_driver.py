import json
from logging import Logger
from typing import Dict, Any

from botocore.exceptions import ClientError
from mypy_boto3_cloudformation import CloudFormationClient


class CloudFormationDriver:
    def __init__(self, cloudformation_client: CloudFormationClient, logger: Logger):
        self.__cloudformation_client = cloudformation_client
        self.__logger = logger

    def get_physical_resource_id(self, cloudformation_stack_name, logical_resource_id):
        describe_stack_resource_result = self.__cloudformation_client.describe_stack_resource(
            StackName=cloudformation_stack_name,
            LogicalResourceId=logical_resource_id
        )

        return describe_stack_resource_result['StackResourceDetail']['PhysicalResourceId']

    def ensure_stack_is_up_to_date(self, cloudformation_stack_name: str, stack_template_data: Dict[str, Any]):
        self.__logger.info('Ensuring CloudFormation stack is up-to-date...')

        try:
            self.__cloudformation_client.create_stack(
                StackName=cloudformation_stack_name,
                TemplateBody=json.dumps(stack_template_data),
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
                OnFailure='DELETE'
            )

            create_stack_waiter = self.__cloudformation_client.get_waiter('stack_create_complete')
            create_stack_waiter.wait(StackName=cloudformation_stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30))

        except ClientError as client_error:
            # noinspection PyUnresolvedReferences
            if client_error.response['Error']['Code'] != 'AlreadyExistsException':
                raise client_error

            self.__cloudformation_client.update_stack(
                StackName=cloudformation_stack_name,
                TemplateBody=json.dumps(stack_template_data),
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND'],
            )

            update_stack_waiter = self.__cloudformation_client.get_waiter('stack_update_complete')
            update_stack_waiter.wait(StackName=cloudformation_stack_name, WaiterConfig=dict(Delay=3, MaxAttempts=30))

        self.__logger.info('CloudFormation stack is up-to-date.')
