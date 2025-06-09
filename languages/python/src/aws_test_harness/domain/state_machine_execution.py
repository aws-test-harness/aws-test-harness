from abc import ABCMeta, abstractmethod
from typing import Optional


class StateMachineExecution(metaclass=ABCMeta):
    @property
    @abstractmethod
    def status(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def output(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def error(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def cause(self) -> Optional[str]:
        pass

    @abstractmethod
    def wait_for_completion(self) -> None:
        pass
