from logging import Logger

from boto3 import Session

from aws_test_harness.infrastructure.boto_aws_resource_factory import BotoAwsResourceFactory
from aws_test_harness.infrastructure.cloudformation_aws_resource_registry import CloudFormationAwsResourceRegistry
from aws_test_harness.infrastructure.serverless_invocation_post_office import ServerlessInvocationPostOffice
from aws_test_harness.infrastructure.thread_based_repeating_task_scheduler import ThreadBasedRepeatingTaskScheduler
from aws_test_harness.domain.test_harness import TestHarness

__all__ = ["aws_test_harness", "TestHarness"]


def aws_test_harness(test_stack_name: str, aws_profile: str, logger: Logger) -> TestHarness:
    boto_session = Session(profile_name=aws_profile)
    aws_resource_registry = CloudFormationAwsResourceRegistry(test_stack_name, boto_session)

    return TestHarness(
        aws_resource_registry,
        ServerlessInvocationPostOffice(
            aws_resource_registry.get_resource_arn('AWSTestHarnessTestDoubleInvocationQueue'),
            aws_resource_registry.get_resource_arn('AWSTestHarnessTestDoubleInvocationTable'),
            boto_session,
            logger
        ),
        ThreadBasedRepeatingTaskScheduler(logger),
        BotoAwsResourceFactory(boto_session, aws_resource_registry, logger)
    )
