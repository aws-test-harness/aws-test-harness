from logging import Logger

from boto3 import Session

from aws_test_harness_test_support.test_cloudformation_stack import TestCloudFormationStack


class TestS3BucketStack(TestCloudFormationStack):
    # Tell pytest to treat this class as a normal class
    __test__ = False

    def __init__(self, stack_name: str, logger: Logger, boto_session: Session):
        super().__init__(stack_name, logger, boto_session)

    def ensure_exists(self) -> None:
        self.ensure_state_is(
            AWSTemplateFormatVersion='2010-09-09',
            Resources=dict(
                Bucket=dict(
                    Type='AWS::S3::Bucket',
                    Properties=dict(
                        PublicAccessBlockConfiguration=dict(
                            BlockPublicAcls=True,
                            BlockPublicPolicy=True,
                            IgnorePublicAcls=True,
                            RestrictPublicBuckets=True
                        ),
                        BucketEncryption=dict(
                            ServerSideEncryptionConfiguration=[
                                dict(ServerSideEncryptionByDefault=dict(SSEAlgorithm='AES256'))
                            ]
                        ),
                        LifecycleConfiguration=dict(Rules=[dict(Status='Enabled', ExpirationInDays=1)])
                    )
                )
            )
        )

    @property
    def bucket_name(self) -> str:
        return self.get_stack_resource_physical_id('Bucket')
