import boto3


class DynamoDBResultsInbox:

    def __init__(self, results_table_name, logger):
        super().__init__()
        self.__results_table = boto3.resource('dynamodb').Table(results_table_name)
        self.__logger = logger

    def try_get_exit_code_for(self, ecs_task_definition_arn, container_name, invocation_id):
        get_item_result = self.__results_table.get_item(
            Key={'partitionKey': f'{ecs_task_definition_arn}#{container_name}#{invocation_id}'}
        )
        exit_code_string = get_item_result.get('Item', {}).get('result', {}).get('exitCode')

        if exit_code_string is not None:
            exit_code = int(exit_code_string)
            self.__logger.info("Found result", exitCode=exit_code)
            return exit_code
        else:
            return None
