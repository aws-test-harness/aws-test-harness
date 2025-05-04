from typing import Dict, Any


class TestDoubleInvocationMessagingResourceFactory:
    @staticmethod
    def generate_queue_resource() -> Dict[str, Any]:
        return dict(
            Type='AWS::SQS::Queue',
            Properties=dict(MessageRetentionPeriod=60)
        )

    @staticmethod
    def generate_invocations_table() -> Dict[str, Any]:
        return dict(
            Type='AWS::DynamoDB::Table',
            Properties=dict(
                BillingMode='PAY_PER_REQUEST',
                KeySchema=[dict(AttributeName="id", KeyType="HASH")],
                AttributeDefinitions=[dict(AttributeName="id", AttributeType="S")],
                TimeToLiveSpecification=dict(AttributeName="ttl", Enabled=True)
            )
        )
