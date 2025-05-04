from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Invocation:
    id: str
    target: str
    payload: Dict[str, Any]
