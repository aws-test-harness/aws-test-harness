from typing import List, Dict


class TaskContext:
    def __init__(self, command_args: List[str], environment_vars: Dict[str, str]):
        self.command_args = command_args
        self.environment_vars = environment_vars