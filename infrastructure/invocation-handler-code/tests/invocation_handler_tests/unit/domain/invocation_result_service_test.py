from time import sleep
from unittest.mock import ANY
from uuid import uuid4

import pytest

from aws_test_harness_test_support.mocking import mock_class, when_calling, verify, as_calls, typed_call
from invocation_handler_tests.support.builders.invocation_builder import an_invocation_with
from test_double_invocation_handler_code.domain.invocation_result_retrieval_timeout_exception import InvocationResultRetrievalTimeoutException
from test_double_invocation_handler_code.domain.invocation import Invocation
from test_double_invocation_handler_code.domain.invocation_post_office import InvocationPostOffice
from test_double_invocation_handler_code.domain.invocation_result_service import InvocationResultService
from test_double_invocation_handler_code.domain.retrieval_attempt import RetrievalAttempt

LONG_TIMEOUT_MILLIS = 5000


def test_retrieves_result_from_invocation_post_office() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    the_invocation = an_invocation_with(invocation_id=str(uuid4()))
    when_calling(invocation_post_office.maybe_collect_result).invoke(
        lambda invocation: RetrievalAttempt(
            'the retrieved result') if invocation == the_invocation
        else RetrievalAttempt.failed()
    )

    invocation_result_service = InvocationResultService(invocation_post_office, LONG_TIMEOUT_MILLIS)

    generated_result = invocation_result_service.generate_result_for(the_invocation)

    assert generated_result == 'the retrieved result'


def test_posts_invocation_before_attempting_to_retrieve_result() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    invocation_result_service = InvocationResultService(invocation_post_office, LONG_TIMEOUT_MILLIS)
    the_invocation = an_invocation_with(invocation_id=str(uuid4()))

    invocation_result_service.generate_result_for(the_invocation)

    verify(invocation_post_office).had_calls(
        as_calls(
            typed_call(InvocationPostOffice).post_invocation(the_invocation),
            typed_call(InvocationPostOffice).maybe_collect_result(ANY)
        ),
        any_order=False
    )


def test_keeps_trying_to_retrieve_result_until_available() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    the_invocation = an_invocation_with(invocation_id=str(uuid4()))
    when_calling(invocation_post_office.maybe_collect_result).respond_with(
        RetrievalAttempt.failed(),
        RetrievalAttempt.failed(),
        RetrievalAttempt('the retrieved result')
    )

    invocation_result_service = InvocationResultService(invocation_post_office, LONG_TIMEOUT_MILLIS)

    generated_result = invocation_result_service.generate_result_for(the_invocation)

    assert generated_result == 'the retrieved result'


def test_raises_timeout_exception_if_no_result_retrieved_before_timeout() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    invocation_id = str(uuid4())
    the_invocation = an_invocation_with(invocation_id=invocation_id)

    def maybe_collect_result(_: Invocation) -> RetrievalAttempt:
        sleep(20 / 1000)
        return RetrievalAttempt.failed()

    when_calling(invocation_post_office.maybe_collect_result).invoke(maybe_collect_result)

    invocation_result_service = InvocationResultService(invocation_post_office, 10)

    with pytest.raises(
            InvocationResultRetrievalTimeoutException,
            match=f'Timed out after 10ms waiting for result for invocation {invocation_id}'
    ):
        invocation_result_service.generate_result_for(the_invocation)
