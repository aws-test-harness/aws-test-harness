from logging import getLogger
from typing import Mapping, Any, TypedDict, Dict, NotRequired

LOGGER = getLogger()


class CloudFormationMacroEvent(TypedDict):
    requestId: str
    accountId: str
    region: str
    fragment: Dict[str, Any]
    templateParameterValues: Dict[str, Any]


class CloudFormationMacroResponse(TypedDict):
    requestId: str
    status: str
    fragment: Dict[str, Any]
    errorMessage: NotRequired[str]


def handler(event: CloudFormationMacroEvent, _: Any) -> CloudFormationMacroResponse:
    original_fragment = event['fragment']

    LOGGER.info("Received CloudFormation template fragment", extra=dict(fragment=original_fragment))

    parameter_values: Mapping[str, Any] = event['templateParameterValues']

    for s3_bucket_id in parameter_values['AWSTestHarnessS3Buckets']:
        original_fragment['Resources'][f'{s3_bucket_id}AWSTestHarnessS3Bucket'] = dict(
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

    LOGGER.info("Returning updated CloudFormation template fragment", extra=dict(fragment=original_fragment))

    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": original_fragment
    }
