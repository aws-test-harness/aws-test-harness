import requests


class HttpECSMetadataSource:

    def __init__(self, metadata_uri):
        super().__init__()
        self.__metadata_uri = metadata_uri

    def fetch_task_metadata(self):
        container_response = requests.get(self.__metadata_uri, timeout=5)
        container_response.raise_for_status()
        container_metadata = container_response.json()

        task_response = requests.get(f"{self.__metadata_uri}/task", timeout=5)
        task_response.raise_for_status()
        task_metadata = task_response.json()

        task_family = task_metadata['Family']
        container_name = container_metadata['Name']
        arn_parts = task_metadata['TaskARN'].split(':')
        arn_prefix = ':'.join(arn_parts[:5])
        task_definition_arn = f"{arn_prefix}:task-definition/{task_family}:{task_metadata['Revision']}"

        return dict(
            taskDefinition=dict(arn=task_definition_arn, family=task_family),
            containerName=container_name
        )
