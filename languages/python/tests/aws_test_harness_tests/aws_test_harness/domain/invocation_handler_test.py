from aws_test_harness.domain.invocation_handler import InvocationHandler
from aws_test_harness.domain.invocation_post_office import InvocationPostOffice
from aws_test_harness_tests.support.builders.invocation_builder import an_invocation_with
from aws_test_harness_tests.support.mocking import mock_class, verify, when_calling


def test_posts_generated_result_for_invocation_collected_from_post_office() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    the_invocation = an_invocation_with(invocation_id='the id')
    when_calling(invocation_post_office.maybe_collect_invocation).always_return(the_invocation)

    invocation_handler = InvocationHandler(
        invocation_post_office,
        get_invocation_result=lambda invocation: "the result" if invocation == the_invocation else None
    )

    invocation_handler.handle_pending_invocation()

    verify(invocation_post_office.post_result).was_called_once_with(
        "the id",
        dict(value="the result")
    )


def test_does_not_post_a_result_if_no_invocation_collected() -> None:
    invocation_post_office = mock_class(InvocationPostOffice)
    when_calling(invocation_post_office.maybe_collect_invocation).always_return(None)

    invocation_handler = InvocationHandler(
        invocation_post_office,
        get_invocation_result=lambda _: "any result"
    )

    invocation_handler.handle_pending_invocation()

    verify(invocation_post_office.post_result).was_not_called()
