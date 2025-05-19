from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Invocation:
    id: str
    target: str
    parameters: Dict[str, Any]
