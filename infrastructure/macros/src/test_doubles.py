import json
from copy import deepcopy


def handler(event, _):
    print(f'Received event: {json.dumps(event)}')

    original_fragment = event['fragment']

    template_parameters = event['templateParameterValues']

    dynamodb_tables_config = json.loads(template_parameters['DynamoDBTables'])
    ecs_task_families = template_parameters.get('ECSTaskFamilies', [])

    new_resources = {}
    new_outputs = {}

    for table_name, table_config in dynamodb_tables_config.items():
        table_logical_id = f'{table_name}Table'
        new_resources[table_logical_id] = create_table_resource_definition(table_config)
        new_resources[f'{table_name}TableInteractionRolePolicy'] = create_table_interaction_role_policy(table_name,
                                                                                                        table_logical_id)
        new_outputs[f'{table_name}DynamoDBTableName'] = dict(
            Value={"Ref": f"{table_name}Table"}
        )

    # Create minimal ECS task definitions
    for task_family in ecs_task_families:
        task_family = task_family.strip()
        if task_family:
            task_def_logical_id = f'{task_family}TaskDefinition'
            new_resources[task_def_logical_id] = create_minimal_ecs_task_definition(task_family)
            new_outputs[f'{task_family}TaskDefinitionArn'] = dict(Value={"Ref": task_def_logical_id})

    updated_fragment = deepcopy(original_fragment)

    updated_fragment['Resources'] = dict(**original_fragment['Resources'], **new_resources)

    original_outputs = original_fragment.get('Outputs', {})

    updated_fragment['Outputs'] = dict(**original_outputs, **new_outputs)

    print(f'Returning fragment: {json.dumps(updated_fragment)}')
    return create_response(event, updated_fragment)


def create_table_interaction_role_policy(table_name, table_logical_id):
    return dict(
        Type='AWS::IAM::RolePolicy',
        Properties=dict(
            PolicyName=f"{table_name}TableInteraction",
            PolicyDocument=dict(
                Version="2012-10-17",
                Statement=[
                    dict(
                        Effect="Allow",
                        Action=[
                            "dynamodb:BatchGetItem",
                            "dynamodb:BatchWriteItem",
                            "dynamodb:ConditionCheckItem",
                            "dynamodb:DescribeTable",
                            "dynamodb:DeleteItem",
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "dynamodb:UpdateItem"
                        ],
                        Resource={
                            "Fn::GetAtt": f"{table_logical_id}.Arn"
                        }
                    )
                ]
            ),
            RoleName={"Ref": "TestDoubleManagerRole"}
        )
    )


def create_table_resource_definition(table_config):
    table_attribute_definitions = [
        dict(
            AttributeName=table_config['PartitionKey']['Name'],
            AttributeType=table_config['PartitionKey']['Type']
        )
    ]
    key_schema = [
        dict(
            AttributeName=table_config['PartitionKey']['Name'],
            KeyType='HASH'
        )
    ]
    if 'SortKey' in table_config:
        table_attribute_definitions.append(
            dict(
                AttributeType=table_config['SortKey']['Type'],
                AttributeName=table_config['SortKey']['Name']
            )
        )
        key_schema.append(
            dict(
                AttributeName=table_config['SortKey']['Name'],
                KeyType='RANGE'
            )
        )

    return dict(
        Type='AWS::DynamoDB::Table',
        Properties=dict(
            AttributeDefinitions=table_attribute_definitions,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=key_schema,
            TimeToLiveSpecification=dict(
                AttributeName='TTL', Enabled=True
            )
        )
    )


def create_minimal_ecs_task_definition(task_family):
    return dict(
        Type='AWS::ECS::TaskDefinition',
        Properties=dict(
            RequiresCompatibilities=['FARGATE'],
            NetworkMode='awsvpc',
            Cpu='256',
            Memory='512',
            ContainerDefinitions=[
                dict(
                    Name=task_family,
                    Image='public.ecr.aws/lambda/python:3.11',
                    Essential=True
                )
            ]
        )
    )


def create_response(event, updated_fragment):
    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }
