from typing import Dict, Any, List

from test_doubles_macro.test_double_s3_bucket_resource_factory import TestDoubleS3BucketResourceFactory


class TestDoubleResourceFactory:
    @staticmethod
    def generate_additional_resources(desired_test_doubles: Dict[str, List[str]]) -> Dict[str, Any]:
        additional_resources = {}

        for s3_bucket_id in desired_test_doubles['AWSTestHarnessS3Buckets']:
            additional_resources[
                f'{s3_bucket_id}AWSTestHarnessS3Bucket'
            ] = TestDoubleS3BucketResourceFactory.generate_resource()

        return additional_resources
