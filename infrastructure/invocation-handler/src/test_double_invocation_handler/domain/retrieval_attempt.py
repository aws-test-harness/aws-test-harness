from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalAttempt:
    value: Any
    succeeded: bool = True

    @staticmethod
    def failed() -> RetrievalAttempt:
        return RetrievalAttempt(None, False)
