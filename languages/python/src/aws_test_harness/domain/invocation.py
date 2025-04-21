from dataclasses import dataclass


@dataclass
class Invocation:
    target: str
    id: str
