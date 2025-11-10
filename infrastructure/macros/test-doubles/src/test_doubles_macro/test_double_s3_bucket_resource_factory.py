from typing import Dict, Any


class TestDoubleS3BucketResourceFactory:
    # Tell pytest to treat this class as a normal class
    __test__ = False

    @staticmethod
    def generate_resource() -> Dict[str, Any]:
        return dict(
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
                        dict(
                            ServerSideEncryptionByDefault=dict(SSEAlgorithm='AES256')
                        )
                    ]
                ),
                LifecycleConfiguration=dict(Rules=[dict(Status='Enabled', ExpirationInDays=1)])
            )
        )
