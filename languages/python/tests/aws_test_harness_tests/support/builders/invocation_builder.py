from typing import Dict, Any, Optional

from aws_test_harness.domain.invocation import Invocation


def any_invocation() -> Invocation:
    return an_invocation_with()


def an_invocation_with(target: str = 'any-invocation-target', invocation_id: str = 'any-invocation-id',
                       parameters: Optional[Dict[str, Any]] = None) -> Invocation:
    return Invocation(target=target, id=invocation_id, parameters=parameters or dict(input=dict()))
