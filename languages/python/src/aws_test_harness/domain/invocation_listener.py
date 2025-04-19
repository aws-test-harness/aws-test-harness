from abc import ABCMeta, abstractmethod


class InvocationListener(metaclass=ABCMeta):
    @abstractmethod
    def listen(self, handle_invocation):
        pass
