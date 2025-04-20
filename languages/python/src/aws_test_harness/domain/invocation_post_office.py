from abc import ABCMeta, abstractmethod


class InvocationPostOffice(metaclass=ABCMeta):
    @abstractmethod
    def maybe_collect_invocation(self):
        pass

    @abstractmethod
    def post_result(self, invocation_id, result):
        pass
