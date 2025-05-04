from unittest.mock import ANY
from uuid import uuid4

from aws_test_harness_test_support.mocking import mock_class, when_calling, verify, as_calls, typed_call
from invocation_handler_tests.support.builders.invocation_builder import an_invocation_with
from test_double_invocation_handler.domain.invocation_post_office import InvocationPostOffice
from test_double_invocation_handler.domain.invocation_result_service import InvocationResultService


def test_retrieves_result_from_invocation_post_office() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    the_invocation = an_invocation_with(invocation_id=str(uuid4()))
    when_calling(invocation_post_office.maybe_collect_result).invoke(
        lambda invocation: 'the retrieved result' if invocation == the_invocation else None
    )

    invocation_result_service = InvocationResultService(invocation_post_office)

    generated_result = invocation_result_service.generate_result_for(the_invocation)

    assert generated_result == 'the retrieved result'


def test_posts_invocation_before_attempting_to_retrieve_result() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    invocation_result_service = InvocationResultService(invocation_post_office)
    the_invocation = an_invocation_with(invocation_id=str(uuid4()))

    invocation_result_service.generate_result_for(the_invocation)

    verify(invocation_post_office).had_calls(
        as_calls(
            typed_call(InvocationPostOffice).post_invocation(the_invocation),
            typed_call(InvocationPostOffice).maybe_collect_result(ANY)
        ),
        any_order=False
    )
