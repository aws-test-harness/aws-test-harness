from dataclasses import dataclass
from typing import List, Dict


@dataclass
class TaskContext:
    command_args: List[str]
    env_vars: Dict[str, str]
