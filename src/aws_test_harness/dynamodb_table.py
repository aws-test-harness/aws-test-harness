from typing import Mapping

from boto3 import Session
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
from mypy_boto3_dynamodb.type_defs import TableAttributeValueTypeDef


class DynamoDBTable:
    def __init__(self, name: str, session: Session):
        self.__name = name
        dynamodb_resource: DynamoDBServiceResource = session.resource('dynamodb')
        self.__table: Table = dynamodb_resource.Table(name)
        self.__scan_paginator = dynamodb_resource.meta.client.get_paginator('scan')

    @property
    def name(self):
        return self.__name

    def get_item(self, key: Mapping[str, TableAttributeValueTypeDef]):
        result = self.__table.get_item(Key=key)
        return result.get('Item')

    def put_item(self, item: Mapping[str, TableAttributeValueTypeDef]):
        self.__table.put_item(Item=item)

    def delete_item(self, key: Mapping[str, TableAttributeValueTypeDef]):
        self.__table.delete_item(Key=key)

    def empty(self):
        attribute_names = [key['AttributeName'] for key in self.__table.key_schema]

        page_iterator = self.__scan_paginator.paginate(
            TableName=self.__name,
            ProjectionExpression=','.join(attribute_names)
        )

        with self.__table.batch_writer() as batch:
            for item in page_iterator.search('Items'):
                key = dict((attribute_name, item[attribute_name]) for attribute_name in attribute_names)
                batch.delete_item(Key=key)
