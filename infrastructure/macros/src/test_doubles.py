import json
import os
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
    
    # Create ECS cluster and execution role if any task families are defined
    if ecs_task_families:
        new_resources['ECSTaskExecutionRole'] = dict(
            Type='AWS::IAM::Role',
            Properties=dict(
                AssumeRolePolicyDocument=dict(
                    Version="2012-10-17",
                    Statement=[
                        dict(
                            Effect="Allow",
                            Principal=dict(Service="ecs-tasks.amazonaws.com"),
                            Action="sts:AssumeRole"
                        )
                    ]
                ),
                ManagedPolicyArns=[
                    "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
                ],
                Policies=[
                    dict(
                        PolicyName="CloudWatchLogsAccess",
                        PolicyDocument=dict(
                            Version="2012-10-17",
                            Statement=[
                                dict(
                                    Effect="Allow",
                                    Action="logs:CreateLogGroup",
                                    Resource={"Fn::Sub": "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/ecs/test-harness/*"}
                                ),
                                dict(
                                    Effect="Allow",
                                    Action=[
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents"
                                    ],
                                    Resource={"Fn::Sub": "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/ecs/test-harness/*:*"}
                                )
                            ]
                        )
                    )
                ]
            )
        )
        new_resources['ECSTaskRole'] = dict(
            Type='AWS::IAM::Role',
            Properties=dict(
                AssumeRolePolicyDocument=dict(
                    Version="2012-10-17",
                    Statement=[
                        dict(
                            Effect="Allow",
                            Principal=dict(Service="ecs-tasks.amazonaws.com"),
                            Action="sts:AssumeRole"
                        )
                    ]
                ),
                Policies=[
                    dict(
                        PolicyName="SQSAccess",
                        PolicyDocument=dict(
                            Version="2012-10-17",
                            Statement=[
                                dict(
                                    Effect="Allow",
                                    Action="sqs:SendMessage",
                                    Resource={"Fn::GetAtt": ["EventsQueue", "Arn"]}
                                )
                            ]
                        )
                    ),
                    dict(
                        PolicyName="S3Access",
                        PolicyDocument=dict(
                            Version="2012-10-17",
                            Statement=[
                                dict(
                                    Effect="Allow",
                                    Action="s3:GetObject",
                                    Resource={"Fn::Sub": "${TestContextBucket.Arn}/*"}
                                )
                            ]
                        )
                    ),
                    dict(
                        PolicyName="DynamoDBAccess",
                        PolicyDocument=dict(
                            Version="2012-10-17",
                            Statement=[
                                dict(
                                    Effect="Allow",
                                    Action="dynamodb:GetItem",
                                    Resource={"Fn::GetAtt": ["ResultsTable", "Arn"]}
                                )
                            ]
                        )
                    )
                ]
            )
        )
        new_resources['ECSCluster'] = dict(
            Type='AWS::ECS::Cluster',
            Properties=dict(
                CapacityProviders=['FARGATE'],
                DefaultCapacityProviderStrategy=[
                    dict(
                        CapacityProvider='FARGATE',
                        Weight=1
                    )
                ]
            )
        )
        new_outputs['ECSClusterArn'] = dict(
            Value={"Fn::GetAtt": ["ECSCluster", "Arn"]}
        )

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
    repository_uri = os.environ.get('ECS_TASK_REPOSITORY_URI')
    return dict(
        Type='AWS::ECS::TaskDefinition',
        Properties=dict(
            RequiresCompatibilities=['FARGATE'],
            NetworkMode='awsvpc',
            Cpu='256',
            Memory='512',
            ExecutionRoleArn={"Fn::GetAtt": ["ECSTaskExecutionRole", "Arn"]},
            TaskRoleArn={"Fn::GetAtt": ["ECSTaskRole", "Arn"]},
            RuntimePlatform=dict(
                CpuArchitecture='ARM64',
                OperatingSystemFamily='LINUX'
            ),
            ContainerDefinitions=[
                dict(
                    Name=task_family,
                    Image=repository_uri,
                    Essential=True,
                    StopTimeout=10,
                    Environment=[
                        dict(Name='EVENTS_QUEUE_URL', Value={'Ref': 'EventsQueue'}),
                        dict(Name='TEST_CONTEXT_BUCKET_NAME', Value={'Ref': 'TestContextBucket'}),
                        dict(Name='RESULTS_TABLE_NAME', Value={'Ref': 'ResultsTable'}),
                        dict(Name='TASK_FAMILY', Value=task_family)
                    ],
                    LogConfiguration=dict(
                        LogDriver='awslogs',
                        Options=dict(
                            **{
                                'awslogs-group': f'/ecs/test-harness/{task_family}',
                                'awslogs-region': {"Ref": "AWS::Region"},
                                'awslogs-stream-prefix': f'{task_family}-task',
                                'awslogs-create-group': 'true'
                            }
                        )
                    )
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
