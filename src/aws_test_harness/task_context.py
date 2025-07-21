from typing import List, Dict


class TaskContext:
    def __init__(self, command_args: List[str], env_vars: Dict[str, str]):
        self.command_args = command_args
        self.env_vars = env_vars