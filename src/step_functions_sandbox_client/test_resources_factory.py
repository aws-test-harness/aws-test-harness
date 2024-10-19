import boto3

from .aws_resource_driver import AWSResourceDriver
from .aws_resource_mocking_engine import AWSResourceMockingEngine
from .boto_session_factory import BotoSessionFactory
from .cloudformation_stack import CloudFormationStack


class TestResourcesFactory:
    def __init__(self, cloudformation_stack_name: str, aws_profile: str):
        self.cloudformation_stack_name = cloudformation_stack_name
        self.aws_profile = aws_profile
        self.__initialised = False

    @property
    def resource_driver(self) -> AWSResourceDriver:
        self.__ensure_initialised()
        return self.__aws_resource_driver

    @property
    def mocking_engine(self) -> AWSResourceMockingEngine:
        self.__ensure_initialised()
        return self.__mocking_engine

    def __ensure_initialised(self):
        if not self.__initialised:
            self.__initialised = True

            developer_boto_session = boto3.session.Session(profile_name=self.aws_profile)

            boto_session_factory = BotoSessionFactory(developer_boto_session)

            cloudformation_stack = CloudFormationStack(self.cloudformation_stack_name, developer_boto_session)

            self.__aws_resource_driver = AWSResourceDriver(
                cloudformation_stack,
                boto_session_factory.create_boto_session_with_assumed_role(
                    cloudformation_stack.get_physical_resource_id_for("TesterRole::Role")
                )
            )

            self.__mocking_engine = AWSResourceMockingEngine(
                cloudformation_stack,
                boto_session_factory.create_boto_session_with_assumed_role(
                    cloudformation_stack.get_physical_resource_id_for("TestDoubles::TestDoubleManagerRole")
                )
            )
