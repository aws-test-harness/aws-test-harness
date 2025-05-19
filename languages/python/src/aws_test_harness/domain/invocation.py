from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Invocation:
    target: str
    id: str
    parameters: Dict[str, Any]
