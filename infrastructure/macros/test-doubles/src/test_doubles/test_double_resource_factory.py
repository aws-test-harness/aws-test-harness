from typing import Dict, Any


class TestDoubleResourceFactory:
    # TODO: Decide whether to take test-double-specific parameters rather than all template parameter values
    @staticmethod
    def generate_additional_resources(parameter_values: Dict[str, str]) -> Dict[str, Any]:
        # TODO: Retrofit tests
        additional_resources = {}

        for s3_bucket_id in parameter_values['AWSTestHarnessS3Buckets']:
            additional_resources[f'{s3_bucket_id}AWSTestHarnessS3Bucket'] = dict(
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

        return additional_resources
