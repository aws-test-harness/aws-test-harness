from step_functions_sandbox_client.cloudformation_stack import CloudFormationStack
from step_functions_sandbox_client.s3_bucket import S3Bucket


class AWSTestDoubleDriver:
    def __init__(self, cloudformation_stack: CloudFormationStack, boto_session):
        self.__cloudformation_stack = cloudformation_stack
        self.__boto_session = boto_session

    def get_s3_bucket(self, logical_resource_id) -> S3Bucket:
        s3_bucket_name = self.__cloudformation_stack.get_physical_resource_id_for(
            f'{logical_resource_id}Bucket'
        )

        s3_bucket = S3Bucket(s3_bucket_name, self.__boto_session)

        return s3_bucket
