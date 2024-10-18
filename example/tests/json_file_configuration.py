import json


class JsonFileConfiguration:
    def __init__(self, config_file_path):
        super().__init__()
        self.config_file_path = config_file_path

    def get_key(self, key: str) -> str:
        with open(self.config_file_path, 'r') as f:
            configuration = json.load(f)

        return configuration[key]
