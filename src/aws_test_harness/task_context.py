from typing import List


class TaskContext:
    def __init__(self, command_args: List[str]):
        self.command_args = command_args