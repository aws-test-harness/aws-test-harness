from aws_test_harness.domain.invocation import Invocation


def an_invocation_with(target: str = 'any-invocation-target', invocation_id: str = 'any-invocation-id') -> Invocation:
    return Invocation(target=target, id=invocation_id)
