# TODO: Retrofit tests
class InvocationHandler:
    def __init__(self, invocation_post_office, get_invocation_result):
        self.__invocation_post_office = invocation_post_office
        self.__get_invocation_result = get_invocation_result

    def handle_pending_invocation(self):
        invocation = self.__invocation_post_office.maybe_collect_invocation()

        if invocation:
            self.__invocation_post_office.post_result(
                invocation.id,
                # TODO: Handle failure to get an invocation result?
                dict(value=self.__get_invocation_result(invocation))
            )
