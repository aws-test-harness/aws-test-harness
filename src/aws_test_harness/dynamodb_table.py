from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table


class DynamoDBTable:
    def __init__(self, name: str, session: Session):
        self.__name = name
        dynamodb_resource: DynamoDBServiceResource = session.resource('dynamodb')
        self.__table: Table = dynamodb_resource.Table(name)

    @property
    def name(self):
        return self.__name

    def get_item(self, key):
        result = self.__table.get_item(Key=key)
        return result.get('Item')

    def put_item(self, item):
        self.__table.put_item(Item=item)
