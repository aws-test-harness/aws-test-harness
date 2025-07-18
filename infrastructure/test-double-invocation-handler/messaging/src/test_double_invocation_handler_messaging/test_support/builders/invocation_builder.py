from typing import Optional, Dict, Any

from test_double_invocation_handler_messaging.domain.invocation import Invocation


def an_invocation_with(invocation_id: str = 'any-invocation-id', invocation_target: str = 'any-invocation-target',
                       parameters: Optional[Dict[str, Any]] = None) -> Invocation:
    return Invocation(
        id=invocation_id,
        target=invocation_target,
        parameters=parameters if parameters else dict()
    )
