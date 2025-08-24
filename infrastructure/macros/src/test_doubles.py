import json
import os
from copy import deepcopy


def handler(event, _):
    print(f'Received event: {json.dumps(event)}')

    original_fragment = event['fragment']

    new_resources = {}
    new_outputs = {}

    template_parameters = event['templateParameterValues']

    dynamodb_tables_config = json.loads(template_parameters.get('DynamoDBTables', '{}'))

    for table_name, table_config in dynamodb_tables_config.items():
        table_logical_id = f'{table_name}Table'
        new_resources[table_logical_id] = dynamodb_table(table_config)
        new_resources[f'{table_name}TableInteractionRolePolicy'] = dynamodb_table_interaction_role_policy_on(
            "TestDoubleManagerRole", table_name, table_logical_id
        )
        new_outputs[f'{table_name}DynamoDBTableName'] = dict(
            Value={"Ref": f"{table_name}Table"}
        )

    ecs_task_families_config = json.loads(template_parameters.get('ECSTaskFamilies', '{}'))

    create_ecs_task_dependencies = False

    container_image = os.environ.get('ECS_TASK_REPOSITORY_URI')
    ecs_task_logical_ids = dict(
        TaskRole="ECSTaskRole",
        ExecutionRole="ECSTaskExecutionRole",
        LogGroup='ECSTaskLogGroup'
    )

    for task_family, task_config in ecs_task_families_config.items():
        containers = task_config.get('Containers', [])
        if containers:
            create_ecs_task_dependencies = True
            task_def_logical_id = f'{task_family}TaskDefinition'
            new_resources[task_def_logical_id] = ecs_task_definition_with_containers(
                task_family, containers, container_image,
                ecs_task_logical_ids
            )

            new_outputs[f'{task_family}TaskDefinitionArn'] = dict(Value={"Ref": task_def_logical_id})

    if create_ecs_task_dependencies:
        log_groups_prefix = os.environ['LOG_GROUPS_PREFIX']
        new_resources[ecs_task_logical_ids['LogGroup']] = log_group(
            {"Fn::Sub": log_groups_prefix + "/aws-test-harness/${AWS::StackName}/ecs-task-containers"})
        new_resources[ecs_task_logical_ids['ExecutionRole']] = ecs_task_execution_role(ecs_task_logical_ids['LogGroup'])
        new_resources[ecs_task_logical_ids['TaskRole']] = ecs_task_role()
        ecs_cluster_logical_id = 'ECSCluster'
        new_resources[ecs_cluster_logical_id] = ecs_cluster()
        new_outputs['ECSClusterArn'] = dict(
            Value={"Fn::GetAtt": ["ECSCluster", "Arn"]}
        )

    updated_fragment = deepcopy(original_fragment)

    updated_fragment['Resources'] = dict(**original_fragment['Resources'], **new_resources)

    original_outputs = original_fragment.get('Outputs', {})

    updated_fragment['Outputs'] = dict(**original_outputs, **new_outputs)

    print(f'Returning fragment: {json.dumps(updated_fragment)}')
    return create_response(event, updated_fragment)


def log_group(name):
    return dict(
        Type="AWS::Logs::LogGroup",
        Properties={
            "LogGroupName": name,
            "RetentionInDays": 1,
        }
    )


def ecs_cluster():
    return dict(
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


def ecs_task_role():
    return dict(
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


def ecs_task_execution_role(log_group_logical_id):
    return dict(
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
                                Action=[
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                Resource={
                                    "Fn::Sub": "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:${" + log_group_logical_id + "}:log-stream:*"
                                }
                            )
                        ]
                    )
                )
            ]
        )
    )


def dynamodb_table_interaction_role_policy_on(role_logical_id, table_name, table_logical_id):
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
            RoleName={"Ref": role_logical_id}
        )
    )


def dynamodb_table(table_config):
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


def create_container_definition(task_family, container_name, image, ecs_task_log_group_logical_id):
    return dict(
        Name=container_name,
        Image=image,
        Essential=True,
        StopTimeout=10,
        Environment=[
            dict(Name='__AWS_TEST_HARNESS__EVENTS_QUEUE_URL', Value={'Ref': 'EventsQueue'}),
            dict(Name='__AWS_TEST_HARNESS__TEST_CONTEXT_BUCKET_NAME', Value={'Ref': 'TestContextBucket'}),
            dict(Name='__AWS_TEST_HARNESS__RESULTS_TABLE_NAME', Value={'Ref': 'ResultsTable'})
        ],
        LogConfiguration=dict(
            LogDriver='awslogs',
            Options=dict(
                **{
                    'awslogs-group': {'Ref': ecs_task_log_group_logical_id},
                    'awslogs-region': {"Ref": "AWS::Region"},
                    'awslogs-stream-prefix': task_family,
                    'awslogs-create-group': 'true'
                }
            )
        )
    )


def ecs_task_definition_with_containers(task_family, containers, container_image, logical_ids):
    return dict(
        Type='AWS::ECS::TaskDefinition',
        Properties=dict(
            RequiresCompatibilities=['FARGATE'],
            NetworkMode='awsvpc',
            Cpu='256',
            Memory='512',
            ExecutionRoleArn={"Fn::GetAtt": [logical_ids['ExecutionRole'], "Arn"]},
            TaskRoleArn={"Fn::GetAtt": [logical_ids['TaskRole'], "Arn"]},
            RuntimePlatform=dict(
                CpuArchitecture='ARM64',
                OperatingSystemFamily='LINUX'
            ),
            ContainerDefinitions=[
                create_container_definition(task_family, container_name, container_image, logical_ids['LogGroup'])
                for container_name in containers
            ]
        )
    )


def create_response(event, updated_fragment):
    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }
