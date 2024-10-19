from uuid import uuid4

import boto3
from boto3 import Session
from mypy_boto3_sts import STSClient


class BotoSessionFactory:

    def __init__(self, boto_session: Session):
        super().__init__()
        self.__boto_session = boto_session

    def create_boto_session_with_assumed_role(self, assumed_role_name: str):
        sts_client: STSClient = self.__boto_session.client("sts")

        identity = sts_client.get_caller_identity()
        aws_account_id = identity["Account"]

        assume_role_response = sts_client.assume_role(
            RoleArn=f'arn:aws:iam::{aws_account_id}:role/{assumed_role_name}',
            RoleSessionName=str(uuid4())
        )

        assumed_role_credentials = assume_role_response["Credentials"]

        return boto3.session.Session(
            aws_access_key_id=assumed_role_credentials["AccessKeyId"],
            aws_secret_access_key=assumed_role_credentials["SecretAccessKey"],
            aws_session_token=assumed_role_credentials["SessionToken"],
            region_name=self.__boto_session.region_name
        )
